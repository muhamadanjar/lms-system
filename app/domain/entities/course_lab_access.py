from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID

from app.domain.entities.base import BaseEntity
from app.domain.exceptions import ValidationError


class CourseLabAccessState:
    ACTIVE = "ACTIVE"
    RELEASED = "RELEASED"

    ALL = (ACTIVE, RELEASED)


@dataclass
class CourseLabAccess(BaseEntity):
    """Satu akses VPS per learner dalam satu course."""

    user_id: str = ""
    course_id: UUID = field(default=None)  # type: ignore[assignment]
    server_id: Optional[UUID] = None
    state: str = CourseLabAccessState.ACTIVE

    def __post_init__(self) -> None:
        if not isinstance(self.user_id, str) or not self.user_id.strip():
            raise ValidationError("user_id is required")
        if self.course_id is None:
            raise ValidationError("course_id is required")
        if self.state not in CourseLabAccessState.ALL:
            raise ValidationError(f"unknown lab access state: {self.state}")
        if self.state == CourseLabAccessState.ACTIVE and self.server_id is None:
            raise ValidationError("ACTIVE access requires a server")
        if self.state == CourseLabAccessState.RELEASED and self.server_id is not None:
            raise ValidationError("RELEASED access must not hold a server")

    def release(self) -> None:
        if self.state == CourseLabAccessState.RELEASED:
            raise ValidationError("lab access is already released")
        self.server_id = None
        self.state = CourseLabAccessState.RELEASED
        self.touch()
