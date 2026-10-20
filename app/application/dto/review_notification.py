from dataclasses import dataclass


@dataclass(frozen=True)
class ReviewNotification:
    """Notification payload for User Management after a task review commits."""

    idempotency_key: str
    recipient_user_id: str
    title: str
    message: str
    event_type: str
    action_url: str
    metadata: dict[str, object]
