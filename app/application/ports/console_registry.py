from dataclasses import dataclass
from datetime import datetime
from typing import Generic, Protocol, TypeVar
from uuid import UUID

S = TypeVar("S")


@dataclass
class ConsoleSlot(Generic[S]):
    session_id: str
    active_since: datetime
    session: S | None = None


class ConsoleRegistry(Protocol):
    def try_acquire(self, server_id: UUID, session_id: str, session: object) -> bool:
        "Reserve the single active console for a server. Returns False when occupied."

    def active(self, server_id: UUID) -> ConsoleSlot | None: ...

    def release(self, server_id: UUID) -> None: ...

    def release_all(self) -> None: ...