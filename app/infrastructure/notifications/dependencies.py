from collections.abc import AsyncIterator

import httpx

from app.config.config import get_settings
from app.infrastructure.notifications.usermanagement_publisher import (
    UserManagementNotificationPublisher,
)


async def get_user_management_notification_publisher() -> AsyncIterator[
    UserManagementNotificationPublisher
]:
    settings = get_settings().usermanagement
    async with httpx.AsyncClient(timeout=settings.timeout_seconds) as client:
        yield UserManagementNotificationPublisher(settings, client)
