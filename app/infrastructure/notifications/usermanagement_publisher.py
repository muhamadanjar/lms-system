import time

import httpx

from app.application.dto.review_notification import ReviewNotification
from app.config.usermanagement import UserManagementSettings


class UserManagementNotificationPublisher:
    def __init__(self, settings: UserManagementSettings, client: httpx.AsyncClient):
        self.settings = settings
        self.client = client
        self._access_token: str | None = None
        self._token_expires_at = 0.0

    def _url(self, path: str) -> str:
        return f"{self.settings.base_url.rstrip('/')}/{path.lstrip('/')}"

    async def _token(self) -> str:
        client_id = self.settings.notification_client_id
        client_secret = self.settings.notification_client_secret.get_secret_value()
        if not client_id or not client_secret:
            raise RuntimeError("UserManagement notification OAuth is not configured")
        now = time.monotonic()
        if self._access_token and now < self._token_expires_at:
            return self._access_token
        response = await self.client.post(
            self._url(self.settings.oauth_token_path),
            data={
                "grant_type": "client_credentials",
                "audience": self.settings.notification_audience,
                "scope": self.settings.notification_scope,
            },
            auth=(client_id, client_secret),
        )
        if not 200 <= response.status_code < 300:
            raise RuntimeError(f"UserManagement OAuth returned {response.status_code}")
        payload = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError("UserManagement OAuth returned an invalid payload")
        token_data = payload.get("data", payload)
        if not isinstance(token_data, dict):
            raise RuntimeError("UserManagement OAuth returned an invalid payload")
        access_token = token_data.get("access_token")
        try:
            lifetime = max(1, int(token_data.get("expires_in", 300)) - 30)
        except (TypeError, ValueError):
            lifetime = 270
        if not isinstance(access_token, str) or not access_token:
            raise RuntimeError("UserManagement OAuth response did not contain an access token")
        self._access_token = access_token
        self._token_expires_at = now + lifetime
        return access_token

    async def publish(self, item: ReviewNotification) -> None:
        token = await self._token()
        response = await self.client.post(
            self._url(self.settings.notification_publish_path),
            headers={
                "Authorization": f"Bearer {token}",
                "Idempotency-Key": item.idempotency_key,
            },
            json={
                "recipient_user_ids": [item.recipient_user_id],
                "title": item.title,
                "message": item.message,
                "event_type": item.event_type,
                "action_url": item.action_url,
                "metadata": item.metadata,
            },
        )
        if not 200 <= response.status_code < 300:
            raise RuntimeError(f"UserManagement notification API returned {response.status_code}")
