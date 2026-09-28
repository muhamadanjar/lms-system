from decimal import Decimal
from uuid import UUID

from sqlalchemy import Column, ForeignKey, Integer, Numeric, String, UniqueConstraint, Uuid, Text
from sqlmodel import Field

from app.domain.value_objects.content import QuestionType
from app.infrastructure.persistence.models.base import ContentTable


class Question(ContentTable, table=True):
    __tablename__ = "questions"
    __table_args__ = (
        UniqueConstraint("quiz_id", "position", name="uq_questions_quiz_position"),
        UniqueConstraint("question_code", name="uq_questions_question_code"),
    )
    quiz_id: UUID = Field(sa_column=Column(Uuid(), ForeignKey("quizzes.id", ondelete="CASCADE", name="fk_questions_quiz_id_quizzes"), nullable=False, index=True))
    prompt: str = Field(sa_type=Text)
    question_type: QuestionType = Field(sa_column=Column(String(10), nullable=False))
    weight: Decimal = Field(default=Decimal("1"), sa_type=Numeric(12, 4), nullable=False)
    position: int = Field(default=0, sa_type=Integer, nullable=False)
    question_code: str = Field(sa_column=Column(String(80), nullable=False, unique=True, index=True))
