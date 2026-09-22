from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, Enum as SAEnum
from sqlmodel import Field, SQLModel

from app.domain.value_objects.content import ContentStatus


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ContentTable(SQLModel):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    slug: str = Field(max_length=160, index=True)
    status: ContentStatus = Field(default=ContentStatus.DRAFT)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


def enum_column(enum_type: type[Enum]) -> Column:
    return Column(SAEnum(enum_type, name=enum_type.__name__.lower(), native_enum=False), nullable=False)
