from typing import Protocol

from app.application.dto.review_notification import ReviewNotification


class NotificationPublisherPort(Protocol):
    """Publish a notification through the owning User Management service."""

    async def publish(self, notification: ReviewNotification) -> None: ...
