from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, Column, ForeignKey, Integer, Text, UniqueConstraint, Uuid
from sqlmodel import Field

from app.infrastructure.persistence.models.base import ContentTable


class Answer(ContentTable, table=True):
    __tablename__ = "answers"
    __table_args__ = (UniqueConstraint("question_id", "position", name="uq_answers_question_position"),)
    question_id: UUID = Field(sa_column=Column(Uuid(), ForeignKey("questions.id", ondelete="CASCADE", name="fk_answers_question_id_questions"), nullable=False, index=True))
    value: str = Field(sa_type=Text)
    position: int = Field(default=0, sa_type=Integer, nullable=False)
    is_correct: Optional[bool] = Field(default=None, sa_type=Boolean)
