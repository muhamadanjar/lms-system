import pytest
from fastapi import HTTPException

from app.application.ports.auth import CurrentUser
from app.presentation.dependencies.auth import require_permission, require_roles
from app.presentation.routers.courses import can_manage


def _user(**kwargs) -> CurrentUser:
    base = {"id": "u-1", "roles": frozenset(), "permissions": frozenset(), "is_superuser": False}
    base.update(kwargs)
    return CurrentUser(**base)


async def test_superuser_bypasses_role_requirement():
    check = require_roles("admin", "instructor")
    user = await check(_user(is_superuser=True))
    assert user.is_superuser is True


async def test_superuser_bypasses_permission_requirement():
    check = require_permission("servers.delete")
    user = await check(_user(is_superuser=True))
    assert user.is_superuser is True


async def test_non_superuser_without_role_is_forbidden():
    with pytest.raises(HTTPException) as exc_info:
        await require_roles("admin")(_user())
    assert exc_info.value.status_code == 403


async def test_non_superuser_without_permission_is_forbidden():
    with pytest.raises(HTTPException) as exc_info:
        await require_permission("servers.delete")(_user())
    assert exc_info.value.status_code == 403


async def test_non_superuser_with_role_and_permission_passes():
    user = await require_roles("admin")(_user(roles=frozenset({"admin"})))
    assert user.id == "u-1"
    user = await require_permission("servers.view")(_user(permissions=frozenset({"servers.view"})))
    assert user.id == "u-1"


def test_can_manage_includes_superuser():
    assert can_manage(_user(is_superuser=True)) is True
    assert can_manage(_user(roles=frozenset({"instructor"}))) is True
    assert can_manage(_user()) is False
