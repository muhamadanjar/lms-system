import json

import httpx

from app.application.ports.auth import CurrentUser
from app.infrastructure.database.dependencies import get_uow
from app.infrastructure.persistence.unit_of_work import SqlModelUnitOfWork
from app.main import app
from app.presentation.dependencies.auth import get_current_user


def _user(*permissions: str) -> CurrentUser:
    return CurrentUser(
        id="admin-1",
        email="admin@example.com",
        roles=frozenset({"admin"}),
        permissions=frozenset(permissions),
    )


async def _client(session, user: CurrentUser):
    async def override_uow():
        yield SqlModelUnitOfWork(session=session)

    async def override_user():
        return user

    app.dependency_overrides[get_uow] = override_uow
    app.dependency_overrides[get_current_user] = override_user
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_servers_crud_flow(session):
    user = _user("servers.view", "servers.create", "servers.update", "servers.delete")
    client = await _client(session, user)
    try:
        async with client:
            response = await client.post(
                "/api/v1/servers",
                json={
                    "name": "api-vps-01",
                    "host": "10.0.0.15",
                    "username": "root",
                    "port": 22,
                    "credential": {"method": "PASSWORD", "password": "hunter2"},
                },
            )
            assert response.status_code == 201
            created = response.json()["data"]
            server_id = created["id"]
            assert created["has_credential"] is True
            assert "credential" not in created and "password" not in json.dumps(created)

            response = await client.get("/api/v1/servers")
            assert response.status_code == 200
            body = response.json()
            assert body["data"][0]["name"] == "api-vps-01"
            assert body["meta"]["total"] == 1

            response = await client.get(f"/api/v1/servers/{server_id}")
            assert response.status_code == 200
            assert response.json()["data"]["host"] == "10.0.0.15"

            response = await client.patch(
                f"/api/v1/servers/{server_id}",
                json={"host": "10.0.0.16"},
            )
            assert response.status_code == 200
            assert response.json()["data"]["host"] == "10.0.0.16"
            assert response.json()["data"]["has_credential"] is True

            response = await client.patch(
                f"/api/v1/servers/{server_id}",
                json={"clear_credential": True},
            )
            assert response.status_code == 200
            assert response.json()["data"]["has_credential"] is False

            response = await client.delete(f"/api/v1/servers/{server_id}")
            assert response.status_code == 204

            response = await client.get(f"/api/v1/servers/{server_id}")
            assert response.status_code == 404
            assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
    finally:
        app.dependency_overrides.clear()


async def test_servers_permission_denied(session):
    client = await _client(session, _user("servers.view"))
    try:
        async with client:
            response = await client.post(
                "/api/v1/servers",
                json={
                    "name": "denied",
                    "host": "10.0.0.1",
                    "username": "root",
                    "credential": {"method": "PASSWORD", "password": "x"},
                },
            )
            assert response.status_code == 403
            assert response.json()["error"]["code"] == "FORBIDDEN"

            response = await client.delete("/api/v1/servers/00000000-0000-0000-0000-000000000000")
            assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


async def test_servers_validation_conflicts(session):
    user = _user("servers.create", "servers.update", "servers.view")
    client = await _client(session, user)
    try:
        async with client:
            response = await client.post(
                "/api/v1/servers",
                json={
                    "name": "dup",
                    "host": "10.0.0.1",
                    "username": "root",
                    "credential": {"method": "PASSWORD", "password": "hunter2"},
                },
            )
            assert response.status_code == 201

            response = await client.post(
                "/api/v1/servers",
                json={
                    "name": "dup",
                    "host": "10.0.0.2",
                    "username": "root",
                    "credential": {"method": "PASSWORD", "password": "x"},
                },
            )
            assert response.status_code == 409
            assert response.json()["error"]["code"] == "RESOURCE_CONFLICT"

            response = await client.post(
                "/api/v1/servers",
                json={
                    "name": "bad-secret",
                    "host": "10.0.0.3",
                    "username": "root",
                    "credential": {"method": "PASSWORD", "password": "-----BEGIN PRIVATE KEY-----"},
                },
            )
            assert response.status_code == 422

            response = await client.patch(
                "/api/v1/servers/00000000-0000-0000-0000-000000000000",
                json={"clear_credential": True, "credential": {"method": "PASSWORD", "password": "new"}},
            )
            assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()