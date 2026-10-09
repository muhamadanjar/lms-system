import json

import httpx
import pytest

from app.application.dto.review_notification import ReviewNotification
from app.config.usermanagement import UserManagementSettings
from app.infrastructure.notifications.usermanagement_publisher import (
    UserManagementNotificationPublisher,
)


@pytest.mark.asyncio
async def test_publish_uses_user_management_internal_api_and_idempotency_key():
    requests = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/oauth/token":
            return httpx.Response(
                200,
                json={"data": {"access_token": "service-token", "expires_in": 600}},
            )
        return httpx.Response(202, json={"success": True})

    settings = UserManagementSettings(
        base_url="https://usermanagement.test",
        notification_client_id="lms-service",
        notification_client_secret="test-secret",
    )
    notification = ReviewNotification(
        idempotency_key="review-event-123",
        recipient_user_id="learner-123",
        title="Hasil review tugas lab: Lulus",
        message="Course: Python\nTugas: Lab 1\nHasil: Lulus",
        event_type="lms.lab_task.review.passed",
        action_url="/courses/python/watch/section/lab-1",
        metadata={"task_id": "task-123", "status": "PASSED"},
    )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), timeout=1.0
    ) as client:
        await UserManagementNotificationPublisher(settings, client).publish(notification)

    assert [request.url.path for request in requests] == [
        "/oauth/token",
        "/internal/v1/notifications",
    ]
    publish_request = requests[1]
    assert publish_request.headers["Authorization"] == "Bearer service-token"
    assert publish_request.headers["Idempotency-Key"] == "review-event-123"
    assert json.loads(publish_request.content) == {
        "recipient_user_ids": ["learner-123"],
        "title": "Hasil review tugas lab: Lulus",
        "message": "Course: Python\nTugas: Lab 1\nHasil: Lulus",
        "event_type": "lms.lab_task.review.passed",
        "action_url": "/courses/python/watch/section/lab-1",
        "metadata": {"task_id": "task-123", "status": "PASSED"},
    }
