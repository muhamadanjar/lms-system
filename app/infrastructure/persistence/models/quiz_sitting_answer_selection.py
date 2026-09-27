from uuid import UUID

from sqlalchemy import Column, ForeignKey, Uuid
from sqlmodel import Field, SQLModel


class QuizSittingAnswerSelection(SQLModel, table=True):
    __tablename__ = "quiz_sitting_answer_selections"

    sitting_question_id: UUID = Field(sa_column=Column(Uuid(), ForeignKey("quiz_sitting_questions.id", ondelete="CASCADE", name="fk_sitting_selections_question"), primary_key=True))
    sitting_option_id: UUID = Field(sa_column=Column(Uuid(), ForeignKey("quiz_sitting_options.id", ondelete="CASCADE", name="fk_sitting_selections_option"), primary_key=True))
