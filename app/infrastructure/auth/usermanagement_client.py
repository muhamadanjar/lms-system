import httpx

from app.application.ports.auth import CurrentUser
from app.config.usermanagement import UserManagementSettings


class AuthServiceUnavailable(Exception):
    """User Management API cannot be reached in time."""


class AuthServiceRejected(Exception):
    """User Management API rejected the supplied token."""


class UserManagementAuthClient:
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
            payload = response.json()
            user_id = str(payload["id"])
            roles = frozenset(str(role).lower() for role in payload.get("roles", []))
            permissions = frozenset(str(permission) for permission in payload.get("permissions", []))
        except (KeyError, TypeError, ValueError) as exc:
            raise AuthServiceRejected from exc
        return CurrentUser(
            id=user_id,
            email=payload.get("email"),
            roles=roles,
            permissions=permissions,
        )
