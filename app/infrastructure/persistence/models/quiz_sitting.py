from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Uuid
from sqlmodel import Field

from app.domain.value_objects.content import QuizAttemptState
from app.infrastructure.persistence.models.base import ContentTable


class QuizSitting(ContentTable, table=True):
    __tablename__ = "quiz_sittings"
    __table_args__ = (
        Index("ix_quiz_sittings_active_learner", "quiz_id", "learner_id", "attempt_state"),
        Index("uq_quiz_sittings_active_key", "active_sitting_key", unique=True),
    )
    quiz_id: UUID = Field(sa_column=Column(Uuid(), ForeignKey("quizzes.id", ondelete="CASCADE", name="fk_quiz_sittings_quiz_id_quizzes"), nullable=False, index=True))
    learner_id: str = Field(max_length=255, nullable=False, index=True)
    attempt_state: QuizAttemptState = Field(sa_column=Column(String(12), nullable=False))
    started_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    submitted_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
    active_sitting_key: Optional[str] = Field(default=None, sa_column=Column(String(600), nullable=True))
    total_score: Optional[int] = Field(default=None, sa_column=Column(Integer, nullable=True))
