from datetime import datetime
from uuid import UUID

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Uuid
from sqlmodel import Field, SQLModel


class QuizSittingQuestionResult(SQLModel, table=True):
    __tablename__ = "quiz_sitting_question_results"

    sitting_question_id: UUID = Field(sa_column=Column(Uuid(), ForeignKey("quiz_sitting_questions.id", ondelete="CASCADE", name="fk_sitting_results_question"), primary_key=True))
    question_code: str = Field(sa_column=Column(String(80), nullable=False))
    outcome: str = Field(sa_column=Column(String(12), nullable=False))
    score: int = Field(sa_column=Column(Integer, nullable=False))
    finalized_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
