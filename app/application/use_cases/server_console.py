from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from app.application.ports.console_registry import ConsoleRegistry
from app.application.ports.credential_cipher import CredentialCipher
from app.application.ports.ssh_bridge import (
    SshBridge,
    SshConsoleError,
    SshSession,
    TermSize,
)
from app.domain.exceptions import NotFoundError


@dataclass
class ConsoleAccepted:
    session: SshSession
    session_id: str
    host_key: str | None


@dataclass
class ConsoleConflict:
    active_since: datetime


class ConsoleNotOpenable(Exception):
    """Fatal failure while opening a console; maps to a `closed` frame."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


class ServerConsoleUseCase:
    def __init__(self, uow_factory: Any, cipher: CredentialCipher, bridge: SshBridge, registry: ConsoleRegistry):
        self.uow_factory = uow_factory
        self.cipher = cipher
        self.bridge = bridge
        self.registry = registry

    async def open(self, server_id: UUID, term: TermSize, session_id: str | None = None) -> ConsoleAccepted | ConsoleConflict:
        session_id = session_id or str(uuid4())
        async with self.uow_factory() as uow:
            server = await uow.servers.get_by_id(server_id)
            if server is None or server.deleted_at is not None:
                raise NotFoundError("server not found")
            if not server.credential_available:
                raise ConsoleNotOpenable("server_error")
            envelope = await uow.servers.get_credential_envelope(server_id)
            if envelope is None:
                raise ConsoleNotOpenable("server_error")
            secret = self.cipher.decrypt(envelope, server_id)

        slot = self.registry.try_acquire(server_id, session_id, session=None)
        if not slot:
            active = self.registry.active(server_id)
            if active is not None:
                return ConsoleConflict(active_since=active.active_since)
            raise ConsoleNotOpenable("server_error")

        try:
            session, learned_host_key = await self.bridge.open(
                host=server.host,
                port=server.port,
                username=server.username,
                method=server.access_method,
                secret=secret,
                passphrase=None,
                expected_host_key=server.host_key,
                term=term,
            )
        except SshConsoleError as exc:
            self.registry.release(server_id)
            raise ConsoleNotOpenable(exc.reason) from exc
        except Exception as exc:
            self.registry.release(server_id)
            raise ConsoleNotOpenable("server_error") from exc

        if server.host_key is None and learned_host_key is not None:
            async with self.uow_factory() as uow:
                current = await uow.servers.get_by_id(server_id)
                if current is not None and current.deleted_at is None and current.host_key is None:
                    current.host_key = learned_host_key
                    current.touch()
                    await uow.servers.update(current)
                    await uow.commit()

        active = self.registry.active(server_id)
        if active is not None:
            active.session = session

        return ConsoleAccepted(session=session, session_id=session_id, host_key=learned_host_key)

    async def takeover(self, server_id: UUID, term: TermSize, session_id: str | None = None) -> ConsoleAccepted | ConsoleConflict:
        slot = self.registry.active(server_id)
        if slot is not None:
            if slot.session is not None:
                await slot.session.close()
            self.registry.release(server_id)
        return await self.open(server_id, term, session_id)

    async def close(self, server_id: UUID) -> None:
        self.registry.release(server_id)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)