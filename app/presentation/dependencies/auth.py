from collections.abc import Callable

from fastapi import Depends, Header, HTTPException, status

from app.application.ports.auth import CurrentUser
from app.config.config import get_settings
from app.infrastructure.auth.usermanagement_client import (
    AuthServiceRejected,
    AuthServiceUnavailable,
    UserManagementAuthClient,
)


async def get_current_user(authorization: str | None = Header(default=None)) -> CurrentUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token is required")
    client = UserManagementAuthClient(get_settings().usermanagement)
    try:
        return await client.get_current_user(authorization)
    except AuthServiceRejected as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token") from exc
    except AuthServiceUnavailable as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Authentication service unavailable") from exc


def require_roles(*roles: str) -> Callable:
    required = tuple(role.lower() for role in roles)

    async def dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not user.has_any_role(required):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return user

    return dependency


require_content_editor = require_roles("admin", "instructor")
