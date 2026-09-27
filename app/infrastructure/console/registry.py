import threading
from datetime import datetime, timezone
from uuid import UUID

from app.application.ports.console_registry import ConsoleSlot


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class InMemoryConsoleRegistry:
    """In-process single-active-console registry.

    lms-system is a single instance, so an in-process registry enforces the
    one-console-per-server contract.
    """

    def __init__(self) -> None:
        self._slots: dict[UUID, ConsoleSlot] = {}
        self._lock = threading.Lock()

    def try_acquire(self, server_id: UUID, session_id: str, session: object) -> bool:
        with self._lock:
            if server_id in self._slots:
                return False
            self._slots[server_id] = ConsoleSlot(
                session_id=session_id,
                active_since=utc_now(),
                session=session,
            )
            return True

    def active(self, server_id: UUID) -> ConsoleSlot | None:
        with self._lock:
            return self._slots.get(server_id)

    def release(self, server_id: UUID) -> None:
        with self._lock:
            self._slots.pop(server_id, None)

    def release_all(self) -> None:
        with self._lock:
            self._slots.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._slots)