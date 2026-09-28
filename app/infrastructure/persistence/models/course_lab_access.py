from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, ForeignKey, Index, String, Uuid, text
from sqlmodel import Field, SQLModel

from app.infrastructure.persistence.models.base import utc_now


class CourseLabAccess(SQLModel, table=True):
    """Satu baris remote_servers yang dikunci untuk satu user dalam satu course."""

    __tablename__ = "course_lab_access"
    __table_args__ = (
        Index(
            "uq_course_lab_access_user_course_live",
            "user_id",
            "course_id",
            unique=True,
            sqlite_where=text("state = 'ACTIVE'"),
            postgresql_where=text("state = 'ACTIVE'"),
        ),
        Index(
            "uq_course_lab_access_server_active",
            "server_id",
            unique=True,
            sqlite_where=text("state = 'ACTIVE'"),
            postgresql_where=text("state = 'ACTIVE'"),
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: str = Field(max_length=255, index=True)
    course_id: UUID = Field(
        sa_column=Column(Uuid(), ForeignKey("courses.id", ondelete="CASCADE", name="fk_course_lab_access_course_id_courses"), nullable=False, index=True)
    )
    server_id: Optional[UUID] = Field(
        default=None,
        sa_column=Column(Uuid(), ForeignKey("remote_servers.id", ondelete="SET NULL", name="fk_course_lab_access_server_id_remote_servers"), nullable=True, index=True),
    )
    state: str = Field(default="ACTIVE", sa_column=Column(String(8), nullable=False, index=True))
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
