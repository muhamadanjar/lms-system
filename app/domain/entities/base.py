from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.exceptions import ValidationError
from app.domain.value_objects.content import ContentStatus, Slug


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class BaseEntity:
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def touch(self) -> None:
        self.updated_at = utc_now()


@dataclass
class ContentEntity(BaseEntity):
    slug: Slug = field(default_factory=lambda: Slug("content"))
    status: ContentStatus = ContentStatus.DRAFT

    def __post_init__(self) -> None:
        if self.created_at.tzinfo is None or self.updated_at.tzinfo is None:
            raise ValidationError("created_at and updated_at must be timezone-aware")
        if self.updated_at < self.created_at:
            raise ValidationError("updated_at cannot precede created_at")

    def change_slug(self, slug: str) -> None:
        if str(self.slug) != slug:
            raise ValidationError("content slugs are immutable")

    def change_status(self, status: ContentStatus) -> None:
        self.status = ContentStatus(status)
        self.touch()
