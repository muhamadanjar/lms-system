from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, ForeignKey, UniqueConstraint, Uuid
from sqlmodel import Field, SQLModel

from app.infrastructure.persistence.models.base import utc_now


class CourseInstructor(SQLModel, table=True):
    """Satu assignment instructor ke satu course; satu course boleh punya banyak instructor."""

    __tablename__ = "course_instructors"
    __table_args__ = (
        UniqueConstraint("course_id", "user_id", name="uq_course_instructors_course_user"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: str = Field(max_length=255, index=True)
    course_id: UUID = Field(
        sa_column=Column(
            Uuid(),
            ForeignKey("courses.id", ondelete="CASCADE", name="fk_course_instructors_course_id_courses"),
            nullable=False,
            index=True,
        )
    )
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    
