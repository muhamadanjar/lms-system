from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EnrollmentCreate(BaseModel):
    user_id: str = Field(min_length=1, max_length=255)


class CourseLabAccessRead(BaseModel):
    """Learner-facing lab access. Tidak ada kredensial atau referensi secret."""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: str
    course_id: UUID
    server_id: UUID | None
    state: str
    created_at: datetime
    updated_at: datetime
