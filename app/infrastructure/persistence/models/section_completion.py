from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, ForeignKey, UniqueConstraint, Uuid
from sqlmodel import Field, SQLModel

from app.infrastructure.persistence.models.base import utc_now


class SectionCompletion(SQLModel, table=True):
    __tablename__ = "section_completions"
    __table_args__ = (UniqueConstraint("learner_id", "section_id", name="uq_section_completions_learner_section"),)
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    learner_id: str = Field(max_length=255, index=True)
    section_id: UUID = Field(sa_column=Column(Uuid(), ForeignKey("sections.id", ondelete="CASCADE", name="fk_section_completions_section_id_sections"), nullable=False, index=True))
    completed_at: datetime = Field(default_factory=utc_now, sa_column=Column(DateTime(timezone=True), nullable=False))
