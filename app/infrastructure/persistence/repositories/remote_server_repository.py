from base64 import b64decode, b64encode
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.application.ports.credential_cipher import CredentialCipher, CredentialEnvelope
from app.domain.entities.remote_server import RemoteServer
from app.domain.exceptions import NotFoundError
from app.domain.repositories.remote_server import RemoteServerRepository
from app.infrastructure.persistence.models.remote_server import RemoteServer as RemoteServerRow


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SqlModelRemoteServerRepository(RemoteServerRepository):
    def __init__(self, session: AsyncSession, cipher: CredentialCipher | Callable[[], CredentialCipher]):
        self.session = session
        self._cipher_factory: Callable[[], CredentialCipher] = cipher if callable(cipher) else (lambda: cipher)
        self._cipher: CredentialCipher | None = None

    @property
    def _resolved_cipher(self) -> CredentialCipher:
        if self._cipher is None:
            self._cipher = self._cipher_factory()
        return self._cipher

    async def create(self, server: RemoteServer) -> RemoteServer:
        row = RemoteServerRow(
            id=server.id,
            name=server.name,
            host=server.host,
            port=server.port,
            username=server.username,
            access_method=server.access_method,
            host_key=server.host_key,
            created_at=server.created_at,
            updated_at=server.updated_at,
        )
        if server.credential is not None:
            self._apply_credential(row, server)
        self.session.add(row)
        await self.session.flush()
        return self._map_row(row)

    async def get_by_id(self, server_id: UUID) -> RemoteServer | None:
        row = await self.session.get(RemoteServerRow, server_id)
        return self._map_row(row) if row is not None else None

    async def get_by_name(self, name: str) -> RemoteServer | None:
        statement = select(RemoteServerRow).where(RemoteServerRow.name == name).limit(1)
        row = (await self.session.exec(statement)).scalars().first()
        return self._map_row(row) if row is not None else None

    async def list(
        self,
        offset: int = 0,
        limit: int = 20,
        search: str | None = None,
        include_deleted: bool = False,
    ) -> list[RemoteServer]:
        statement = select(RemoteServerRow)
        if not include_deleted:
            statement = statement.where(RemoteServerRow.deleted_at.is_(None))
        if search:
            like = f"%{search}%"
            statement = statement.where(or_(RemoteServerRow.name.ilike(like), RemoteServerRow.host.ilike(like)))
        statement = statement.order_by(RemoteServerRow.created_at.desc()).offset(offset).limit(limit)
        rows = (await self.session.exec(statement)).scalars().all()
        return [self._map_row(row) for row in rows]

    async def count(self, search: str | None = None, include_deleted: bool = False) -> int:
        statement = select(func.count()).select_from(RemoteServerRow)
        if not include_deleted:
            statement = statement.where(RemoteServerRow.deleted_at.is_(None))
        if search:
            like = f"%{search}%"
            statement = statement.where(or_(RemoteServerRow.name.ilike(like), RemoteServerRow.host.ilike(like)))
        return int((await self.session.exec(statement)).scalar_one())

    async def get_credential_envelope(self, server_id: UUID) -> CredentialEnvelope | None:
        row = await self.session.get(RemoteServerRow, server_id)
        if row is None or row.credential_ciphertext is None:
            return None
        return CredentialEnvelope(
            ciphertext=b64decode(row.credential_ciphertext),
            nonce=b64decode(row.credential_nonce),
            key_version=row.credential_key_version or 1,
        )

    async def update(self, server: RemoteServer) -> RemoteServer:
        row = await self.session.get(RemoteServerRow, server.id)
        if row is None:
            raise NotFoundError("server not found")
        row.name = server.name
        row.host = server.host
        row.port = server.port
        row.username = server.username
        row.access_method = server.access_method
        row.host_key = server.host_key
        row.updated_at = server.updated_at
        if getattr(server, "_clear_credential", False):
            row.credential_ciphertext = None
            row.credential_nonce = None
            row.credential_key_version = None
        elif server.credential is not None:
            self._apply_credential(row, server)
        await self.session.flush()
        return self._map_row(row)

    async def soft_delete(self, server_id: UUID) -> bool:
        row = await self.session.get(RemoteServerRow, server_id)
        if row is None or row.deleted_at is not None:
            return False
        row.deleted_at = utc_now()
        row.updated_at = row.deleted_at
        await self.session.flush()
        return True

    def _apply_credential(self, row: RemoteServerRow, server: RemoteServer) -> None:
        envelope = self._resolved_cipher.encrypt(server.credential, server.id)
        row.credential_ciphertext = b64encode(envelope.ciphertext).decode("ascii")
        row.credential_nonce = b64encode(envelope.nonce).decode("ascii")
        row.credential_key_version = envelope.key_version

    def _map_row(self, row: RemoteServerRow) -> RemoteServer:
        return RemoteServer(
            id=row.id,
            name=row.name,
            host=row.host,
            port=row.port,
            username=row.username,
            access_method=row.access_method,
            credential=None,
            credential_available=row.credential_ciphertext is not None,
            host_key=row.host_key,
            deleted_at=row.deleted_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
