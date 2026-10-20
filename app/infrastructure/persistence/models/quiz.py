from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, Column, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlmodel import Field

from app.infrastructure.persistence.models.base import ContentTable


class Quiz(ContentTable, table=True):
    __tablename__ = "quizzes"
    __table_args__ = (
        UniqueConstraint("section_id", name="uq_quizzes_section"),
        UniqueConstraint("course_id", "slug", name="uq_quizzes_course_slug"),
        CheckConstraint("passing_score >= 0 AND passing_score <= 100", name="ck_quizzes_passing_score_range"),
    )
    course_id: UUID = Field(sa_column=Column(Uuid(), ForeignKey("courses.id", ondelete="CASCADE", name="fk_quizzes_course_id_courses"), nullable=False, index=True))
    section_id: UUID | None = Field(default=None, sa_column=Column(Uuid(), ForeignKey("sections.id", ondelete="SET NULL", name="fk_quizzes_section_id_sections"), nullable=True, index=True))
    title: str = Field(max_length=255)
    description: Optional[str] = Field(default=None, sa_type=Text)
    is_exam: bool = Field(default=False, sa_column=Column(Boolean, nullable=False, server_default="false"))
    max_attempts: int = Field(default=1, sa_column=Column(Integer, nullable=False, server_default="1"))
    passing_score: int = Field(default=70, sa_column=Column(Integer, nullable=False, server_default="70"))
    answer_policy: str = Field(default="SINGLE", sa_column=Column(String(12), nullable=False, server_default="SINGLE"))
