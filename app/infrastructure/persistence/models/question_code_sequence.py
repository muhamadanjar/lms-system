from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String
from sqlmodel import Field, SQLModel

from app.infrastructure.persistence.models.base import utc_now


class QuestionCodeSequence(SQLModel, table=True):
    __tablename__ = "question_code_sequences"

    name: str = Field(default="question_code", sa_column=Column(String(80), primary_key=True))
    next_value: int = Field(default=1, sa_column=Column(Integer, nullable=False))
    updated_at: datetime = Field(default_factory=utc_now, sa_column=Column(DateTime(timezone=True), nullable=False))
