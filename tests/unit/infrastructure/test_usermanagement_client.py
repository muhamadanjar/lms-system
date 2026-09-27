import httpx
import pytest

from app.config.usermanagement import UserManagementSettings
from app.infrastructure.auth.usermanagement_client import (
    AuthServiceRejected,
    AuthServiceUnavailable,
    UserManagementAuthClient,
)


def _settings() -> UserManagementSettings:
    return UserManagementSettings(
        base_url="http://um-test",
        auth_info_path="/auth/info",
        timeout_seconds=1.0,
    )


class _FakeResponse:
    def __init__(self, status_code: int, payload=None):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class _FakeAsyncClient:
    response: _FakeResponse | None = None
    error: Exception | None = None
    seen: list[dict] = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url, headers=None):
        type(self).seen.append({"url": url, "headers": headers})
        if type(self).error is not None:
            raise type(self).error
        assert type(self).response is not None
        return type(self).response


@pytest.fixture
def fake_transport(monkeypatch):
    _FakeAsyncClient.response = None
    _FakeAsyncClient.error = None
    _FakeAsyncClient.seen = []
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)
    return _FakeAsyncClient


async def test_parses_enveloped_auth_info_with_role_objects(fake_transport):
    """Live /auth/info shape: APIResponse envelope + RoleSerializer objects."""
    fake_transport.response = _FakeResponse(200, {
        "success": True,
        "data": {
            "id": "user-1",
            "email": "admin@example.com",
            "roles": [{"id": "r1", "name": "Admin", "is_active": True}],
            "permissions": ["servers.view", "servers.create"],
        },
        "message": "Data User",
    })
    user = await UserManagementAuthClient(_settings()).get_current_user("Bearer token")
    assert user.id == "user-1"
    assert user.email == "admin@example.com"
    assert user.roles == frozenset({"admin"})
    assert user.permissions == frozenset({"servers.view", "servers.create"})
    assert user.is_superuser is False
    assert fake_transport.seen[0]["headers"] == {"Authorization": "Bearer token"}


async def test_parses_is_superuser_flag(fake_transport):
    fake_transport.response = _FakeResponse(200, {
        "success": True,
        "data": {"id": "root-1", "roles": [], "permissions": [], "is_superuser": True},
    })
    user = await UserManagementAuthClient(_settings()).get_current_user("Bearer token")
    assert user.is_superuser is True


async def test_accepts_bare_user_object_with_string_roles(fake_transport):
    fake_transport.response = _FakeResponse(200, {
        "id": "user-2",
        "roles": ["Instructor"],
        "permissions": [],
    })
    user = await UserManagementAuthClient(_settings()).get_current_user("Bearer token")
    assert user.id == "user-2"
    assert user.roles == frozenset({"instructor"})


async def test_rejected_on_401(fake_transport):
    fake_transport.response = _FakeResponse(401, {"detail": "unauthorized"})
    with pytest.raises(AuthServiceRejected):
        await UserManagementAuthClient(_settings()).get_current_user("Bearer bad")


async def test_unavailable_on_500(fake_transport):
    fake_transport.response = _FakeResponse(500, {})
    with pytest.raises(AuthServiceUnavailable):
        await UserManagementAuthClient(_settings()).get_current_user("Bearer token")


async def test_rejected_when_envelope_has_no_user_id(fake_transport):
    fake_transport.response = _FakeResponse(200, {"success": True, "data": {"roles": []}})
    with pytest.raises(AuthServiceRejected):
        await UserManagementAuthClient(_settings()).get_current_user("Bearer token")
