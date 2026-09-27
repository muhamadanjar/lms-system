from uuid import UUID, uuid4

from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint, Uuid, Text
from sqlmodel import Field, SQLModel


class QuizSittingQuestion(SQLModel, table=True):
    __tablename__ = "quiz_sitting_questions"
    __table_args__ = (
        UniqueConstraint("sitting_id", "question_code", name="uq_sitting_question_code"),
        UniqueConstraint("sitting_id", "position", name="uq_sitting_question_position"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    sitting_id: UUID = Field(sa_column=Column(Uuid(), ForeignKey("quiz_sittings.id", ondelete="CASCADE", name="fk_sitting_questions_sitting"), nullable=False, index=True))
    source_question_id: UUID = Field(sa_column=Column(Uuid(), ForeignKey("questions.id", name="fk_sitting_questions_source_question"), nullable=False))
    question_code: str = Field(sa_column=Column(String(80), nullable=False))
    prompt: str = Field(sa_type=Text)
    question_type: str = Field(sa_column=Column(String(12), nullable=False))
    answer_policy: str = Field(sa_column=Column(String(12), nullable=False))
    position: int = Field(sa_column=Column(Integer, nullable=False))
