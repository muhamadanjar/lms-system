import asyncio
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.application.ports.ssh_bridge import TermSize
from app.domain.entities.remote_server import RemoteServer
from app.domain.exceptions import ConflictError, ValidationError


def _now() -> datetime:
    return datetime.now(timezone.utc)


class FakeSession:
    """In-process fake SSH session for console tests."""

    def __init__(self):
        self._queue: asyncio.Queue[tuple[str, Any]] = asyncio.Queue()
        self.closed = False
        self.term_sizes: list[tuple[int, int]] = []
        self.input_sink: list[str] = []

    async def send_input(self, data: str) -> None:
        self.input_sink.append(data)
        self._queue.put_nowait(("data", f"<echo>{data}"))

    async def resize(self, cols: int, rows: int) -> None:
        self.term_sizes.append((cols, rows))

    async def next_output(self) -> str | None:
        kind, payload = await self._queue.get()
        if kind == "lost":
            return None
        return payload

    async def close(self) -> None:
        self.closed = True
        self._queue.put_nowait(("lost", None))


class FakeBridge:
    def __init__(self):
        self.calls: list[dict] = []
        self.fail: Exception | None = None
        self.host_key = "ssh-ed25519 fake"

    async def open(self, **kwargs) -> tuple[FakeSession, str | None]:
        if self.fail is not None:
            raise self.fail
        self.calls.append(kwargs)
        return FakeSession(), self.host_key


class FakeRegistry:
    def __init__(self):
        self._slots: dict[UUID, Any] = {}

    def try_acquire(self, server_id: UUID, session_id: str, session: object) -> bool:
        if server_id in self._slots:
            return False
        from app.application.ports.console_registry import ConsoleSlot

        self._slots[server_id] = ConsoleSlot(session_id=session_id, active_since=_now(), session=session)
        return True

    def active(self, server_id: UUID):
        return self._slots.get(server_id)

    def release(self, server_id: UUID) -> None:
        self._slots.pop(server_id, None)

    def release_all(self) -> None:
        self._slots.clear()


class InMemoryServers:
    """Domain-only in-memory server store mirroring the repository contract."""

    def __init__(self, cipher=None):
        self._cipher = cipher
        self._by_id: dict[UUID, RemoteServer] = {}
        self._by_name: dict[str, RemoteServer] = {}
        self._envelopes: dict[UUID, object] = {}

    async def create(self, server: RemoteServer):
        if self._by_name.get(server.name) is not None:
            raise ConflictError(f"server '{server.name}' already exists")
        if server.credential is not None and self._cipher is not None:
            self._envelopes[server.id] = self._cipher.encrypt(server.credential.value, server.id)
        out = _without_credential(server)
        self._by_id[server.id] = out
        self._by_name[server.name] = out
        return out

    async def get_by_id(self, server_id: UUID) -> RemoteServer | None:
        return self._by_id.get(server_id)

    async def get_by_name(self, name: str) -> RemoteServer | None:
        for server in self._by_id.values():
            if server.name == name:
                return server
        return None

    async def list(self, offset=0, limit=20, search=None, include_deleted=False):
        items = [s for s in self._by_id.values() if include_deleted or s.deleted_at is None]
        return items[offset : offset + limit]

    async def count(self, search=None, include_deleted=False) -> int:
        return len([s for s in self._by_id.values() if include_deleted or s.deleted_at is None])

    async def get_credential_envelope(self, server_id: UUID):
        return self._envelopes.get(server_id)

    async def update(self, server: RemoteServer):
        if getattr(server, "_clear_credential", False):
            self._envelopes.pop(server.id, None)
            server.credential_available = False
        elif server.credential is not None and self._cipher is not None:
            self._envelopes[server.id] = self._cipher.encrypt(server.credential.value, server.id)
            server.credential_available = True
        out = _without_credential(server)
        self._by_id[server.id] = out
        self._by_name[server.name] = out
        return out

    async def soft_delete(self, server_id: UUID) -> bool:
        server = self._by_id.get(server_id)
        if server is None or server.deleted_at is not None:
            return False
        server.deleted_at = _now()
        return True


def _without_credential(server: RemoteServer) -> RemoteServer:
    import dataclasses

    return dataclasses.replace(server, credential=None)