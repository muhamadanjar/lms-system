import asyncio
import contextlib

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.application.ports.auth import CurrentUser
from app.application.use_cases.server_console import ServerConsoleUseCase
from app.domain.entities.remote_server import RemoteServer
from app.domain.value_objects.content import AccessMethod
from app.domain.value_objects.remote_server import ServerCredential
from app.infrastructure.console.registry import InMemoryConsoleRegistry
from app.infrastructure.crypto.aesgcm import AesGcmCredentialCipher
from app.presentation import websocket as ws_module
from app.presentation.websocket.console import ws_router
from tests._fakes import FakeBridge, InMemoryServers


@contextlib.asynccontextmanager
async def _uow_cm(servers):
    class UOW:
        def __init__(self):
            self.servers = servers

        async def commit(self):
            return None

    yield UOW()


def _seed_server():
    import uuid

    cipher = AesGcmCredentialCipher(bytes(range(32)))
    servers = InMemoryServers(cipher=cipher)
    server = RemoteServer(
        name=f"console-box-{uuid.uuid4().hex[:8]}",
        host="10.0.0.20",
        port=22,
        username="root",
        access_method=AccessMethod.PASSWORD,
        credential=ServerCredential(method=AccessMethod.PASSWORD, value="hunter2"),
    )
    asyncio.run(servers.create(server))
    return cipher, servers, server.id


def _user(*permissions: str) -> CurrentUser:
    return CurrentUser(
        id="console-user",
        email="console@example.com",
        roles=frozenset({"admin"}),
        permissions=frozenset(permissions),
    )


def _wire(monkeypatch, cipher, servers, use_case, authenticate):
    async def _authenticate(ws):
        return authenticate(ws), None

    def _build():
        return use_case

    def _settings():
        ssh = type("SSH", (), {"ping_interval_seconds": 30})()
        return type("S", (), {"ssh": ssh})()

    monkeypatch.setattr(ws_module.console, "authenticate_websocket", _authenticate)
    monkeypatch.setattr(ws_module.console, "build_console_use_case", _build)
    monkeypatch.setattr(ws_module.console, "get_settings", _settings)


def _ws_path(server_id) -> str:
    return f"/api/v1/servers/{server_id}/console"


def _console_loop(cipher, servers):
    registry = InMemoryConsoleRegistry()
    use_case = ServerConsoleUseCase(
        lambda: _uow_cm(servers),
        cipher,
        FakeBridge(),
        registry,
    )
    return registry, use_case


def test_console_echo_resize_and_ping(monkeypatch):
    cipher, servers, server_id = _seed_server()
    registry, use_case = _console_loop(cipher, servers)
    _wire(monkeypatch, cipher, servers, use_case, lambda _ws: _user("servers.view", "servers.console"))

    app = FastAPI()
    app.include_router(ws_router)

    with TestClient(app) as client:
        with client.websocket_connect(_ws_path(server_id), subprotocols=["bearer.token"]) as ws:
            assert ws.receive_json() == {"type": "ready"}

            ws.send_json({"type": "input", "data": "ls\n"})
            out = ws.receive_json()
            assert out["type"] == "output"
            assert "<echo>ls" in out["data"]

            ws.send_json({"type": "resize", "cols": 120, "rows": 40})
            ws.send_json({"type": "ping"})
            assert ws.receive_json() == {"type": "pong"}

    assert registry.active(server_id) is None


def test_console_conflict_then_takeover(monkeypatch):
    cipher, servers, server_id = _seed_server()
    registry, use_case = _console_loop(cipher, servers)
    _wire(monkeypatch, cipher, servers, use_case, lambda _ws: _user("servers.view", "servers.console"))

    app = FastAPI()
    app.include_router(ws_router)

    with TestClient(app) as client:
        with client.websocket_connect(_ws_path(server_id), subprotocols=["bearer.token"]) as ws1:
            assert ws1.receive_json() == {"type": "ready"}

            with client.websocket_connect(_ws_path(server_id), subprotocols=["bearer.token"]) as ws2:
                conflict = ws2.receive_json()
                assert conflict["type"] == "conflict"

                ws2.send_json({"type": "takeover"})
                assert ws2.receive_json() == {"type": "ready"}

    assert registry.active(server_id) is None


def test_console_denied_when_lacking_permission(monkeypatch):
    cipher, servers, server_id = _seed_server()
    registry, use_case = _console_loop(cipher, servers)
    _wire(monkeypatch, cipher, servers, use_case, lambda _ws: _user("courses.view"))

    app = FastAPI()
    app.include_router(ws_router)

    with TestClient(app) as client:
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(_ws_path(server_id), subprotocols=["bearer.token"]) as ws:
                frame = ws.receive_json()
                assert frame == {"type": "closed", "reason": "permission_error"}
                ws.receive_json()
        assert exc_info.value.code == 4403

    assert registry.active(server_id) is None
