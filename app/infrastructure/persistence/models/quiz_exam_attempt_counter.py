from datetime import datetime
from uuid import UUID

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Uuid
from sqlmodel import Field, SQLModel

from app.infrastructure.persistence.models.base import utc_now


class QuizExamAttemptCounter(SQLModel, table=True):
    __tablename__ = "quiz_exam_attempt_counters"

    quiz_id: UUID = Field(sa_column=Column(Uuid(), ForeignKey("quizzes.id", ondelete="CASCADE", name="fk_exam_counter_quiz"), primary_key=True))
    learner_id: str = Field(sa_column=Column(String(255), primary_key=True))
    finalized_attempts: int = Field(default=0, sa_column=Column(Integer, nullable=False))
    updated_at: datetime = Field(default_factory=utc_now, sa_column=Column(DateTime(timezone=True), nullable=False))
