"""Port for private object storage used by learner task evidence."""

from typing import Protocol


class FileStoragePort(Protocol):
    """Stores and retrieves file bytes without exposing provider details."""

    active_backend: str

    async def put(self, key: str, content: bytes, content_type: str) -> None: ...

    async def get(self, backend: str, key: str) -> bytes: ...

    async def delete(self, backend: str, key: str) -> None: ...
