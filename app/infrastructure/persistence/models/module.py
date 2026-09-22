from typing import Optional
from uuid import UUID

from sqlalchemy import Column, ForeignKey, Integer, Text, UniqueConstraint, Uuid
from sqlmodel import Field

from app.infrastructure.persistence.models.base import ContentTable


class Module(ContentTable, table=True):
    __tablename__ = "modules"
    __table_args__ = (UniqueConstraint("course_id", "position", name="uq_modules_course_position"),)
    course_id: UUID = Field(sa_column=Column(Uuid(), ForeignKey("courses.id", ondelete="CASCADE", name="fk_modules_course_id_courses"), nullable=False, index=True))
    title: str = Field(max_length=255)
    description: Optional[str] = Field(default=None, sa_type=Text)
    position: int = Field(default=0, sa_type=Integer, nullable=False)
