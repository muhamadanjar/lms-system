import httpx
import pytest

from app.application.ports.user_directory import DirectoryUnavailable, EmailAmbiguous, EmailNotFound
from app.config.usermanagement import UserManagementSettings
from app.infrastructure.auth.usermanagement_directory import UserManagementDirectory


def _directory(handler) -> UserManagementDirectory:
    settings = UserManagementSettings(base_url="http://um.test", timeout_seconds=5.0)
    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, timeout=5.0)
    return UserManagementDirectory(settings, client=client)


def _payload(users):
    return {"success": True, "data": users, "message": "ok"}


async def test_exact_match_returns_id():
    async def handler(request):
        assert request.url.params["search"] == "a@x.id"
        assert request.headers["authorization"] == "Bearer admin-token"
        return httpx.Response(200, json=_payload([{"id": "u-1", "email": "other@x.id"}, {"id": "u-2", "email": "a@X.id"}]))

    directory = _directory(handler)
    assert await directory.find_user_id_by_email("a@x.id", "Bearer admin-token") == "u-2"


async def test_bare_list_envelope_tolerated():
    async def handler(request):
        return httpx.Response(200, json=[{"id": "u-3", "email": "b@x.id"}])

    directory = _directory(handler)
    assert await directory.find_user_id_by_email("B@X.ID", "Bearer t") == "u-3"


async def test_no_match_raises_not_found():
    async def handler(request):
        return httpx.Response(200, json=_payload([{"id": "u-1", "email": "other@x.id"}]))

    with pytest.raises(EmailNotFound):
        await _directory(handler).find_user_id_by_email("ghost@x.id", "Bearer t")


async def test_multiple_exact_matches_raise_ambiguous():
    async def handler(request):
        return httpx.Response(200, json=_payload([{"id": "u-1", "email": "dup@x.id"}, {"id": "u-2", "email": "DUP@x.id"}]))

    with pytest.raises(EmailAmbiguous):
        await _directory(handler).find_user_id_by_email("dup@x.id", "Bearer t")


async def test_server_error_raises_unavailable():
    async def handler(request):
        return httpx.Response(503, json={})

    with pytest.raises(DirectoryUnavailable):
        await _directory(handler).find_user_id_by_email("a@x.id", "Bearer t")


async def test_network_error_raises_unavailable():
    async def handler(request):
        raise httpx.ConnectError("down")

    with pytest.raises(DirectoryUnavailable):
        await _directory(handler).find_user_id_by_email("a@x.id", "Bearer t")
