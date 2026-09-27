import httpx

from app.application.ports.auth import CurrentUser
from app.config.usermanagement import UserManagementSettings


class AuthServiceUnavailable(Exception):
    """User Management API cannot be reached in time."""


class AuthServiceRejected(Exception):
    """User Management API rejected the supplied token."""


def _normalize_role(role: object) -> str:
    """Extract the role name from a RoleSerializer object or plain string."""
    if isinstance(role, dict):
        return str(role.get("name", "")).lower()
    return str(role).lower()


class UserManagementAuthClient:
    """Client for the User Management API auth endpoints.

    Contract with GET {base_url}/auth/info: 200 returns the APIResponse
    envelope ``{"success": true, "data": {...user...}, "message": ...}``
    where ``data.roles`` are ``{"id","name",...}`` objects (not plain
    strings) and ``data.permissions`` are permission name strings.
    A bare (unenveloped) user object is also accepted for tolerance.
    """

    def __init__(self, settings: UserManagementSettings):
        self.settings = settings

    async def get_current_user(self, authorization: str) -> CurrentUser:
        try:
            async with httpx.AsyncClient(timeout=self.settings.timeout_seconds) as client:
                response = await client.get(
                    self.settings.auth_info_url,
                    headers={"Authorization": authorization},
                )
        except httpx.RequestError as exc:
            raise AuthServiceUnavailable from exc

        if response.status_code in (401, 403):
            raise AuthServiceRejected
        if response.status_code >= 500:
            raise AuthServiceUnavailable
        if response.status_code != 200:
            raise AuthServiceRejected

        try:
            body = response.json()
        except ValueError as exc:
            raise AuthServiceRejected from exc
        if not isinstance(body, dict):
            raise AuthServiceRejected
        payload = body.get("data", body)
        if not isinstance(payload, dict):
            raise AuthServiceRejected
        try:
            user_id = str(payload["id"])
            roles = frozenset(
                name for name in (_normalize_role(role) for role in payload.get("roles", [])) if name
            )
            permissions = frozenset(str(permission) for permission in payload.get("permissions", []))
        except (KeyError, TypeError, ValueError) as exc:
            raise AuthServiceRejected from exc
        return CurrentUser(
            id=user_id,
            email=payload.get("email"),
            roles=roles,
            permissions=permissions,
            is_superuser=bool(payload.get("is_superuser", False)),
        )
