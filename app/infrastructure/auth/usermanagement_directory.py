import httpx

from app.application.ports.user_directory import DirectoryUnavailable, EmailAmbiguous, EmailNotFound, UserDirectory
from app.config.usermanagement import UserManagementSettings


class UserManagementDirectory(UserDirectory):
    """Email lookup via User Management ``GET /users?search=``.

    Accepts both enveloped (``{"data": [...]}``) and bare-list payloads,
    mirroring the tolerance of the auth client. Only an exact
    (case-insensitive) single email match resolves; anything else is
    reported as not found or ambiguous so identities are never misbound.
    """

    def __init__(self, settings: UserManagementSettings, client: httpx.AsyncClient | None = None):
        self.settings = settings
        self._client = client

    def _users_url(self) -> str:
        return f"{self.settings.base_url.rstrip('/')}/users"

    async def find_user_id_by_email(self, email: str, authorization: str | None) -> str:
        wanted = email.strip().lower()
        headers = {"Authorization": authorization} if authorization else {}
        try:
            if self._client is not None:
                response = await self._client.get(self._users_url(), params={"search": email.strip()}, headers=headers)
            else:
                async with httpx.AsyncClient(timeout=self.settings.timeout_seconds) as client:
                    response = await client.get(self._users_url(), params={"search": email.strip()}, headers=headers)
        except httpx.RequestError as exc:
            raise DirectoryUnavailable("user directory unreachable") from exc
        if response.status_code != 200:
            raise DirectoryUnavailable(f"user directory returned {response.status_code}")
        try:
            body = response.json()
        except ValueError as exc:
            raise DirectoryUnavailable("user directory returned invalid payload") from exc
        users = body.get("data", body) if isinstance(body, dict) else body
        if not isinstance(users, list):
            raise DirectoryUnavailable("user directory returned invalid payload")
        matches = [u for u in users if isinstance(u, dict) and str(u.get("email", "")).lower() == wanted and u.get("id") is not None]
        if not matches:
            raise EmailNotFound(f"no user found for email: {email.strip()}")
        if len(matches) > 1:
            raise EmailAmbiguous(f"multiple users found for email: {email.strip()}")
        return str(matches[0]["id"])
