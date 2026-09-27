from collections.abc import Callable
from typing import Any
from uuid import UUID

from app.domain.entities.remote_server import RemoteServer
from app.domain.exceptions import ConflictError, NotFoundError
from app.domain.value_objects.content import AccessMethod
from app.domain.value_objects.remote_server import ServerCredential


class ServerInventoryUseCase:
    def __init__(self, uow_factory: Callable[[], Any]):
        self.uow_factory = uow_factory

    async def list(self, page: int, page_size: int, search: str | None = None) -> tuple[list[RemoteServer], int]:
        async with self.uow_factory() as uow:
            items = await uow.servers.list((page - 1) * page_size, page_size, search=search)
            total = await uow.servers.count(search=search)
        return items, total

    async def get(self, server_id: UUID) -> RemoteServer:
        async with self.uow_factory() as uow:
            server = await uow.servers.get_by_id(server_id)
            if server is None or server.deleted_at is not None:
                raise NotFoundError("server not found")
        return server

    async def create(
        self,
        *,
        name: str,
        host: str,
        username: str,
        port: int = 22,
        access_method: AccessMethod,
        credential: ServerCredential | None = None,
    ) -> RemoteServer:
        async with self.uow_factory() as uow:
            existing = await uow.servers.get_by_name(name)
            if existing is not None:
                raise ConflictError(f"server '{name}' already exists")
            server = RemoteServer(
                name=name,
                host=host,
                port=port,
                username=username,
                access_method=access_method,
                credential=credential,
            )
            await uow.servers.create(server)
            await uow.commit()
        server.credential = None
        return server

    async def update(
        self,
        server_id: UUID,
        *,
        name: str | None = None,
        host: str | None = None,
        username: str | None = None,
        port: int | None = None,
        access_method: AccessMethod | None = None,
        credential: ServerCredential | None = None,
        clear_credential: bool = False,
    ) -> RemoteServer:
        if credential is not None and clear_credential:
            from app.domain.exceptions import ValidationError

            raise ValidationError("cannot set a credential and clear it at the same time")
        async with self.uow_factory() as uow:
            server = await uow.servers.get_by_id(server_id)
            if server is None or server.deleted_at is not None:
                raise NotFoundError("server not found")
            if name is not None and name != server.name:
                other = await uow.servers.get_by_name(name)
                if other is not None and other.id != server_id:
                    raise ConflictError(f"server '{name}' already exists")
                server.name = name
            if host is not None and host != server.host:
                server.host = host
                server.host_key = None
            if port is not None:
                server.port = port
            if username is not None:
                server.username = username
            if access_method is not None:
                server.access_method = access_method
            if credential is not None:
                if credential.method is not server.access_method:
                    from app.domain.exceptions import ValidationError

                    raise ValidationError("credential method must match access method")
                server.credential = credential
            elif clear_credential:
                server._clear_credential = True
                server.credential_available = False
            server.touch()
            await uow.servers.update(server)
            await uow.commit()
        server.credential = None
        return server

    async def delete(self, server_id: UUID) -> None:
        async with self.uow_factory() as uow:
            server = await uow.servers.get_by_id(server_id)
            if server is None:
                raise NotFoundError("server not found")
            if server.deleted_at is None:
                await uow.servers.soft_delete(server_id)
                await uow.commit()


def credential_from_input(access_method: AccessMethod, password: str | None, public_key: str | None, passphrase: str | None) -> ServerCredential | None:
    if access_method is AccessMethod.PASSWORD:
        return ServerCredential(method=access_method, value=password or "")
    if public_key is not None:
        return ServerCredential(method=access_method, value=public_key or "", passphrase=passphrase)
    return None