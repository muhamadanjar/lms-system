from uuid import UUID

from sqlalchemy import Column, ForeignKey, UniqueConstraint, Uuid
from sqlmodel import Field

from app.infrastructure.persistence.models.base import ContentTable


class Quiz(ContentTable, table=True):
    __tablename__ = "quizzes"
    __table_args__ = (UniqueConstraint("section_id", name="uq_quizzes_section"),)
    section_id: UUID = Field(sa_column=Column(Uuid(), ForeignKey("sections.id", ondelete="CASCADE", name="fk_quizzes_section_id_sections"), nullable=False, index=True))
