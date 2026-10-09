from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CourseInstructorAssign(BaseModel):
    user_id: str = Field(min_length=1, max_length=255)


class CourseInstructorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    course_id: UUID
    user_id: str
    created_at: datetime
    updated_at: datetime
