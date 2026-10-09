from dataclasses import dataclass, field
from uuid import UUID

from app.domain.entities.base import BaseEntity
from app.domain.exceptions import ValidationError


@dataclass
class CourseInstructor(BaseEntity):
    """Satu assignment instructor ke satu course; satu course boleh banyak instructor."""

    course_id: UUID = field(default=None)  # type: ignore[assignment]
    user_id: str = ""

    def __post_init__(self) -> None:
        if self.course_id is None:
            raise ValidationError("course_id is required")
        if not isinstance(self.user_id, str) or not self.user_id.strip():
            raise ValidationError("user_id is required")
