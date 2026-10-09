from pydantic import BaseModel, Field

from app.application.dto.learner_progress import CourseProgressDTO


class SectionProgressRead(BaseModel):
    module_slug: str
    section_slug: str
    content_type: str
    is_accessible: bool
    is_complete: bool
    requires_pass: bool
    state: str


class CourseWatchPositionRead(BaseModel):
    module_slug: str
    section_slug: str


class CourseWatchPositionWrite(BaseModel):
    module_slug: str = Field(min_length=1, max_length=255)
    section_slug: str = Field(min_length=1, max_length=255)


class CourseProgressRead(BaseModel):
    enrollment_status: str | None
    course_state: str
    progression_mode: str
    completion_mode: str
    sections: list[SectionProgressRead]
    last_opened: CourseWatchPositionRead | None = None


def course_progress_read(value: CourseProgressDTO) -> CourseProgressRead:
    return CourseProgressRead(
        enrollment_status=value.enrollment_status,
        course_state=value.course_state,
        progression_mode=value.progression_mode,
        completion_mode=value.completion_mode,
        sections=[SectionProgressRead(**item.__dict__) for item in value.sections],
        last_opened=(
            CourseWatchPositionRead(**value.last_opened.__dict__)
            if value.last_opened is not None
            else None
        ),
    )
