from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID

from app.domain.entities.base import BaseEntity, utc_now
from app.domain.exceptions import ValidationError


class EnrollmentStatus:
    ENROLLED = "ENROLLED"
    COMPLETED = "COMPLETED"
    WITHDRAWN = "WITHDRAWN"

    LIVE = (ENROLLED,)
    ALL = (ENROLLED, COMPLETED, WITHDRAWN)


@dataclass
class Enrollment(BaseEntity):
    """Satu episode kepesertaan learner dalam satu course."""

    user_id: str = ""
    course_id: UUID = field(default=None)  # type: ignore[assignment]
    status: str = EnrollmentStatus.ENROLLED
    enrolled_at: datetime = field(default_factory=utc_now)
    completed_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if not isinstance(self.user_id, str) or not self.user_id.strip():
            raise ValidationError("user_id is required")
        if self.course_id is None:
            raise ValidationError("course_id is required")
        if self.status not in EnrollmentStatus.ALL:
            raise ValidationError(f"unknown enrollment status: {self.status}")
        for name in ("enrolled_at", "created_at", "updated_at"):
            if getattr(self, name).tzinfo is None:
                raise ValidationError(f"{name} must be timezone-aware")
        if self.completed_at is not None and self.completed_at.tzinfo is None:
            raise ValidationError("completed_at must be timezone-aware")
        if self.status == EnrollmentStatus.COMPLETED and self.completed_at is None:
            raise ValidationError("COMPLETED enrollment requires completed_at")
        if self.status != EnrollmentStatus.COMPLETED and self.completed_at is not None:
            raise ValidationError("only COMPLETED enrollment may hold completed_at")

    def complete(self, completed_at: Optional[datetime] = None) -> None:
        if self.status != EnrollmentStatus.ENROLLED:
            raise ValidationError("only ENROLLED enrollment can be completed")
        completed_at = completed_at or utc_now()
        if completed_at.tzinfo is None:
            raise ValidationError("completed_at must be timezone-aware")
        self.completed_at = completed_at
        self.status = EnrollmentStatus.COMPLETED
        self.touch()

    def withdraw(self) -> None:
        if self.status != EnrollmentStatus.ENROLLED:
            raise ValidationError("only ENROLLED enrollment can be withdrawn")
        self.status = EnrollmentStatus.WITHDRAWN
        self.touch()
