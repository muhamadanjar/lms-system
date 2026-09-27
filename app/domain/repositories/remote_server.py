from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities.remote_server import RemoteServer


class RemoteServerRepository(ABC):
    @abstractmethod
    async def create(self, server: RemoteServer) -> RemoteServer: ...

    @abstractmethod
    async def get_by_id(self, server_id: UUID) -> RemoteServer | None: ...

    @abstractmethod
    async def get_by_name(self, name: str) -> RemoteServer | None: ...

    @abstractmethod
    async def list(
        self,
        offset: int = 0,
        limit: int = 20,
        search: str | None = None,
        include_deleted: bool = False,
    ) -> list[RemoteServer]: ...

    @abstractmethod
    async def count(self, search: str | None = None, include_deleted: bool = False) -> int: ...

    @abstractmethod
    async def get_credential_envelope(self, server_id: UUID) -> object | None: ...

    @abstractmethod
    async def update(self, server: RemoteServer) -> RemoteServer: ...

    @abstractmethod
    async def soft_delete(self, server_id: UUID) -> bool: ...