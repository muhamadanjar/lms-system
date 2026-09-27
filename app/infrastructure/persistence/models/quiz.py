from uuid import UUID

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, UniqueConstraint, Uuid
from sqlmodel import Field

from app.infrastructure.persistence.models.base import ContentTable


class Quiz(ContentTable, table=True):
    __tablename__ = "quizzes"
    __table_args__ = (UniqueConstraint("section_id", name="uq_quizzes_section"),)
    section_id: UUID = Field(sa_column=Column(Uuid(), ForeignKey("sections.id", ondelete="CASCADE", name="fk_quizzes_section_id_sections"), nullable=False, index=True))
    is_exam: bool = Field(default=False, sa_column=Column(Boolean, nullable=False, server_default="false"))
    max_attempts: int = Field(default=1, sa_column=Column(Integer, nullable=False, server_default="1"))
    answer_policy: str = Field(default="SINGLE", sa_column=Column(String(12), nullable=False, server_default="SINGLE"))
