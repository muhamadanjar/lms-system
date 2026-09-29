from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, ForeignKey, Index, String, Uuid, text
from sqlmodel import Field, SQLModel

from app.infrastructure.persistence.models.base import utc_now


class Enrollment(SQLModel, table=True):
    """Satu episode kepesertaan learner dalam satu course."""

    __tablename__ = "enrollments"
    __table_args__ = (
        Index(
            "uq_enrollments_user_course_live",
            "user_id",
            "course_id",
            unique=True,
            sqlite_where=text("status = 'ENROLLED'"),
            postgresql_where=text("status = 'ENROLLED'"),
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: str = Field(max_length=255, index=True)
    course_id: UUID = Field(
        sa_column=Column(Uuid(), ForeignKey("courses.id", ondelete="CASCADE", name="fk_enrollments_course_id_courses"), nullable=False, index=True)
    )
    status: str = Field(default="ENROLLED", sa_column=Column(String(10), nullable=False, index=True))
    enrolled_at: datetime = Field(default_factory=utc_now)
    completed_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
