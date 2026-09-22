from datetime import datetime
from uuid import UUID

from sqlalchemy import Column, DateTime, Uuid
from sqlmodel import Field, SQLModel

from app.infrastructure.persistence.models.base import utc_now


class ContentSlugRegistry(SQLModel, table=True):
    __tablename__ = "content_slug_registry"
    slug: str = Field(primary_key=True, max_length=160)
    content_id: UUID = Field(nullable=False, index=True)
    content_kind: str = Field(max_length=80, nullable=False)
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
