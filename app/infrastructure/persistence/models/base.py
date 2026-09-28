from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import String
from sqlmodel import Field, SQLModel

from app.domain.value_objects.content import ContentStatus


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ContentTable(SQLModel):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    slug: str = Field(max_length=160, index=True)
    status: ContentStatus = Field(
        default=ContentStatus.DRAFT,
        sa_type=String(9),
        nullable=False,
    )
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
