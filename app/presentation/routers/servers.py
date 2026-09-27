from fastapi import APIRouter, Depends, Response, status
from uuid import UUID

from app.application.ports.auth import CurrentUser
from app.application.use_cases.server_inventory import ServerInventoryUseCase
from app.domain.exceptions import ValidationError
from app.infrastructure.database.dependencies import get_uow
from app.infrastructure.persistence.unit_of_work import SqlModelUnitOfWork
from app.presentation.dependencies.auth import get_current_user, require_permission
from app.presentation.schemas.content import ApiResponse, PaginationQuery
from app.presentation.schemas.server import (
    ServerCreate,
    ServerRead,
    ServerUpdate,
    server_read,
)
from fastapi.exceptions import HTTPException

router = APIRouter(prefix="/api/v1/servers", tags=["Servers"])


def use_cases(uow: SqlModelUnitOfWork) -> ServerInventoryUseCase:
    return ServerInventoryUseCase(lambda: uow)


@router.get("", response_model=ApiResponse[list[ServerRead]])
async def list_servers(
    query: PaginationQuery = Depends(),
    _user: CurrentUser = Depends(require_permission("servers.view")),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    items, total = await use_cases(uow).list(query.page, query.page_size, query.search)
    return ApiResponse(
        data=[server_read(item) for item in items],
        meta={"page": query.page, "page_size": query.page_size, "total": total},
    )


@router.post("", response_model=ApiResponse[ServerRead], status_code=status.HTTP_201_CREATED)
async def create_server(
    payload: ServerCreate,
    _user: CurrentUser = Depends(require_permission("servers.create")),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    access_method = payload.credential.method if payload.credential else None
    server = await use_cases(uow).create(
        name=payload.name,
        host=payload.host,
        username=payload.username,
        port=payload.port,
        access_method=access_method,
        credential=payload.credential.to_credential() if payload.credential else None,
    )
    return ApiResponse(data=server_read(server), meta={"resource": "server"})


@router.get("/{server_id}", response_model=ApiResponse[ServerRead])
async def get_server(
    server_id: UUID,
    _user: CurrentUser = Depends(require_permission("servers.view")),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    server = await use_cases(uow).get(server_id)
    return ApiResponse(data=server_read(server), meta={"resource": "server"})


@router.patch("/{server_id}", response_model=ApiResponse[ServerRead])
async def update_server(
    server_id: UUID,
    payload: ServerUpdate,
    _user: CurrentUser = Depends(require_permission("servers.update")),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    try:
        server = await use_cases(uow).update(
            server_id,
            name=payload.name,
            host=payload.host,
            username=payload.username,
            port=payload.port,
            access_method=payload.credential.method if payload.credential else None,
            credential=payload.credential.to_credential() if payload.credential else None,
            clear_credential=payload.clear_credential,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ApiResponse(data=server_read(server), meta={"resource": "server"})


@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_server(
    server_id: UUID,
    _user: CurrentUser = Depends(require_permission("servers.delete")),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    await use_cases(uow).delete(server_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)