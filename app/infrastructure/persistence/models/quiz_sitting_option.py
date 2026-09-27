from uuid import UUID, uuid4

from sqlalchemy import Boolean, Column, ForeignKey, Integer, UniqueConstraint, Uuid, Text
from sqlmodel import Field, SQLModel


class QuizSittingOption(SQLModel, table=True):
    __tablename__ = "quiz_sitting_options"
    __table_args__ = (UniqueConstraint("sitting_question_id", "position", name="uq_sitting_option_position"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    sitting_question_id: UUID = Field(sa_column=Column(Uuid(), ForeignKey("quiz_sitting_questions.id", ondelete="CASCADE", name="fk_sitting_options_question"), nullable=False, index=True))
    source_answer_id: UUID = Field(sa_column=Column(Uuid(), ForeignKey("answers.id", name="fk_sitting_options_source_answer"), nullable=False))
    value: str = Field(sa_type=Text)
    position: int = Field(sa_column=Column(Integer, nullable=False))
    is_correct: bool = Field(sa_column=Column(Boolean, nullable=False))
