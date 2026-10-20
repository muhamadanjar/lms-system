from typing import Optional
from sqlalchemy import Text
from sqlalchemy import CheckConstraint, Column, String
from sqlmodel import Field, SQLModel

from app.infrastructure.persistence.models.base import ContentTable
from app.domain.value_objects.learning_policy import CompletionMode, ProgressionMode


class Course(ContentTable, table=True):
    __tablename__ = "courses"
    __table_args__ = (
        CheckConstraint("progression_mode IN ('FREE','SEQUENTIAL')", name="ck_courses_progression_mode"),
        CheckConstraint("completion_mode IN ('SELF_LEARNING','ADMIN_REVIEW')", name="ck_courses_completion_mode"),
    )
    title: str = Field(max_length=255)
    description: Optional[str] = Field(default=None, sa_type=Text)
    sequence: int = Field(default=0, nullable=True)
    progression_mode: ProgressionMode = Field(default=ProgressionMode.FREE, sa_column=Column(String(12), nullable=False, server_default="FREE"))
    completion_mode: CompletionMode = Field(default=CompletionMode.SELF_LEARNING, sa_column=Column(String(16), nullable=False, server_default="SELF_LEARNING"))
