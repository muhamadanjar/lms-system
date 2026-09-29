from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EnrollmentCreate(BaseModel):
    user_id: str = Field(min_length=1, max_length=255)
    enrolled_at: datetime | None = None


class EnrollmentComplete(BaseModel):
    completed_at: datetime | None = None


class BulkEnrollItem(BaseModel):
    user_id: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=255)


class BulkEnrollRequest(BaseModel):
    users: list[BulkEnrollItem] = Field(min_length=1, max_length=100)


class BulkSkippedItem(BaseModel):
    identifier: str
    reason: str


class BulkFailedItem(BaseModel):
    identifier: str
    reason: str


class BulkEnrollResponse(BaseModel):
    enrolled: list["EnrollmentRead"] = Field(default_factory=list)
    skipped: list[BulkSkippedItem] = Field(default_factory=list)
    failed: list[BulkFailedItem] = Field(default_factory=list)


class EnrollmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: str
    course_id: UUID
    status: str
    enrolled_at: datetime
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
