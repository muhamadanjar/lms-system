import asyncio
import json
from uuid import UUID, uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.application.ports.ssh_bridge import TermSize
from app.application.use_cases.server_console import (
    ConsoleAccepted,
    ConsoleConflict,
    ConsoleNotOpenable,
    ServerConsoleUseCase,
)
from app.config.config import get_settings
from app.domain.exceptions import NotFoundError
from app.infrastructure.console.registry import InMemoryConsoleRegistry
from app.infrastructure.database.manager import database_manager
from app.infrastructure.persistence.unit_of_work import SqlModelUnitOfWork
from app.presentation.dependencies.websocket import WebSocketAuthError, authenticate_websocket

ws_router = APIRouter()

_registry: InMemoryConsoleRegistry | None = None


def get_console_registry() -> InMemoryConsoleRegistry:
    global _registry
    if _registry is None:
        _registry = InMemoryConsoleRegistry()
    return _registry


def create_console_use_case(
    uow_factory,
    cipher,
    bridge,
    registry,
) -> ServerConsoleUseCase:
    return ServerConsoleUseCase(uow_factory, cipher, bridge, registry)


def build_console_use_case() -> ServerConsoleUseCase:
    """Default wiring; component factories are overridable for contract tests."""
    from app.infrastructure.crypto.aesgcm import AesGcmCredentialCipher, encode_credential_key
    from app.infrastructure.ssh.asyncssh_bridge import AsyncSshBridge

    settings = get_settings().ssh
    cipher = AesGcmCredentialCipher(
        encode_credential_key(settings.credential_enc_key),
        settings.credential_key_version,
    )
    bridge = AsyncSshBridge(
        connect_timeout=settings.connect_timeout,
        auth_timeout=settings.auth_timeout,
    )
    registry = get_console_registry()

    async def uow_factory() -> SqlModelUnitOfWork:
        session = await database_manager.create_async_session("default")
        return SqlModelUnitOfWork(session=session)

    return create_console_use_case(uow_factory, cipher, bridge, registry)


def _send(ws: WebSocket, payload: dict, lock: asyncio.Lock) -> "asyncio.Task":
    return asyncio.create_task(_send_async(ws, payload, lock))


async def _send_async(ws: WebSocket, payload: dict, lock: asyncio.Lock) -> None:
    async with lock:
        try:
            await ws.send_text(json.dumps(payload))
        except Exception:
            pass


def _frame_ready() -> dict:
    return {"type": "ready"}


def _frame_output(data: str) -> dict:
    return {"type": "output", "data": data}


def _frame_conflict(active_since) -> dict:
    return {"type": "conflict", "active_since": active_since.isoformat()}


def _frame_closed(reason: str) -> dict:
    return {"type": "closed", "reason": reason}


def _frame_pong() -> dict:
    return {"type": "pong"}


def _frame_ping() -> dict:
    return {"type": "ping"}


async def _output_pump(ws: WebSocket, session, ping_interval: float, lock: asyncio.Lock) -> None:
    while True:
        try:
            chunk = await asyncio.wait_for(session.next_output(), timeout=ping_interval)
        except asyncio.TimeoutError:
            task = _send(ws, _frame_ping(), lock)
            try:
                await task
            except Exception:
                return
            continue
        except Exception:
            chunk = None
        if chunk is None:
            _send(ws, _frame_closed("disconnected"), lock)
            return
        _send(ws, _frame_output(chunk), lock)


async def _safe_close(session) -> None:
    try:
        await session.close()
    except Exception:
        pass


@ws_router.websocket("/api/v1/servers/{server_id}/console")
async def console_websocket(ws: WebSocket, server_id: UUID):
    echo: str | None = None
    try:
        user, echo = await authenticate_websocket(ws)
    except WebSocketAuthError:
        await ws.accept()
        await ws.send_text(json.dumps(_frame_closed("auth_error")))
        await ws.close(code=4401)
        return
    if user is None or (not user.is_superuser and not user.has_permission(("servers.view", "servers.console"))):
        await ws.accept()
        await ws.send_text(json.dumps(_frame_closed("auth_error")))
        await ws.close(code=4403)
        return
    await ws.accept(subprotocol=echo)

    send_lock = asyncio.Lock()
    use_case = build_console_use_case()
    settings = get_settings().ssh
    term = TermSize(cols=110, rows=30)
    session_id = str(uuid4())
    session = None
    output_task: asyncio.Task | None = None

    try:
        result = await use_case.open(server_id, term, session_id)
        if isinstance(result, ConsoleConflict):
            task = _send(ws, _frame_conflict(result.active_since), send_lock)
            await task
            while True:
                frame = await ws.receive_json()
                ftype = frame.get("type")
                if ftype == "takeover":
                    result = await use_case.takeover(server_id, term, session_id)
                    if isinstance(result, ConsoleAccepted):
                        session = result.session
                        task = _send(ws, _frame_ready(), send_lock)
                        await task
                        break
                    task = _send(ws, _frame_conflict(result.active_since), send_lock)
                    await task
                elif ftype == "ping":
                    task = _send(ws, _frame_pong(), send_lock)
                    await task
        else:
            session = result.session
            task = _send(ws, _frame_ready(), send_lock)
            await task

        if session is None:
            return

        output_task = asyncio.create_task(_output_pump(ws, session, settings.ping_interval_seconds, send_lock))

        while True:
            frame = await ws.receive_json()
            ftype = frame.get("type")
            if ftype == "input":
                data = frame.get("data")
                if isinstance(data, str) and data:
                    await session.send_input(data)
            elif ftype == "resize":
                try:
                    cols = int(frame.get("cols"))
                    rows = int(frame.get("rows"))
                except (TypeError, ValueError):
                    continue
                if cols > 0 and rows > 0:
                    term = TermSize(cols=cols, rows=rows)
                    await session.resize(cols, rows)
            elif ftype == "takeover":
                session_id = str(uuid4())
                result = await use_case.takeover(server_id, term, session_id)
                if isinstance(result, ConsoleAccepted):
                    old = session
                    session = result.session
                    if output_task is not None:
                        output_task.cancel()
                        try:
                            await output_task
                        except (asyncio.CancelledError, Exception):
                            pass
                    await _safe_close(old)
                    task = _send(ws, _frame_ready(), send_lock)
                    await task
                    output_task = asyncio.create_task(_output_pump(ws, session, settings.ping_interval_seconds, send_lock))
                else:
                    task = _send(ws, _frame_conflict(result.active_since), send_lock)
                    await task
            elif ftype == "ping":
                task = _send(ws, _frame_pong(), send_lock)
                await task
    except WebSocketDisconnect:
        pass
    except NotFoundError:
        task = _send(ws, _frame_closed("server_deleted"), send_lock)
        await task
    except ConsoleNotOpenable as exc:
        task = _send(ws, _frame_closed(exc.reason), send_lock)
        await task
    except Exception:
        task = _send(ws, _frame_closed("server_error"), send_lock)
        await task
    finally:
        if output_task is not None:
            output_task.cancel()
        if session is not None:
            await _safe_close(session)
        try:
            await use_case.close(server_id)
        except Exception:
            pass
        try:
            await ws.close()
        except Exception:
            pass