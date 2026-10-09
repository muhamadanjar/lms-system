"""Read DTOs for a learner's Course Watch state."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class SectionProgressDTO:
    module_slug: str
    section_slug: str
    content_type: str
    is_accessible: bool
    is_complete: bool
    requires_pass: bool
    state: str


@dataclass(frozen=True)
class CourseWatchPositionDTO:
    module_slug: str
    section_slug: str


@dataclass(frozen=True)
class CourseProgressDTO:
    enrollment_status: str | None
    course_state: str
    progression_mode: str
    completion_mode: str
    sections: tuple[SectionProgressDTO, ...]
    last_opened: CourseWatchPositionDTO | None = None


@dataclass(frozen=True)
class LearnerCourseSummaryDTO:
    course_slug: str
    course_title: str
    course_description: str | None
    enrollment_status: str
    enrolled_at: datetime
    completed_at: datetime | None
    completed_sections: int
    total_sections: int
    percentage: int
    course_state: str
