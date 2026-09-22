from typing import Optional
from uuid import UUID

from sqlalchemy import Column, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlmodel import Field

from app.domain.value_objects.content import SectionContentType
from app.infrastructure.persistence.models.base import ContentTable, enum_column


class Section(ContentTable, table=True):
    __tablename__ = "sections"
    __table_args__ = (UniqueConstraint("module_id", "position", name="uq_sections_module_position"),)
    module_id: UUID = Field(sa_column=Column(Uuid(), ForeignKey("modules.id", ondelete="CASCADE", name="fk_sections_module_id_modules"), nullable=False, index=True))
    title: str = Field(max_length=255)
    description: Optional[str] = Field(default=None, sa_type=Text)
    position: int = Field(default=0, sa_type=Integer, nullable=False)
    content_type: SectionContentType = Field(sa_column=Column(String(10), nullable=False))
    body: Optional[str] = Field(default=None, sa_type=Text)
