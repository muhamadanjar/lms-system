from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.application.ports.auth import CurrentUser
from app.config.config import get_settings
from app.infrastructure.auth.usermanagement_client import (
    AuthServiceRejected,
    AuthServiceUnavailable,
    UserManagementAuthClient,
)

# Shared bearer scheme so OpenAPI emits a securityScheme: Swagger UI renders
# the Authorize button + lock icons, and every route behind get_current_user
# (directly or via require_roles/require_permission) inherits the requirement.
bearer_scheme = HTTPBearer(auto_error=False, description="JWT dari User Management API (kirim sebagai Bearer token)")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser:
    """Extract identity from the Authorization bearer token.

    Only extracts the token and delegates validation to the User Management
    API; authorization decisions stay in the application use cases.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token is required")
    authorization = f"Bearer {credentials.credentials}"
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
        if user.is_superuser:
            return user
        if not user.has_any_role(required):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return user

    return dependency


require_content_editor = require_roles("admin", "instructor")


def require_permission(*permissions: str) -> Callable:
    required = set(permissions)

    async def dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.is_superuser:
            return user
        if not user.has_permission(required):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permission")
        return user

    return dependency
