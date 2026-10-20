from collections.abc import Callable
from app.domain.entities.course import Course
from app.domain.entities.section import Section
from app.domain.exceptions import ValidationError
from app.domain.value_objects.learning_policy import ProgressionMode


def first_blocking_section(course: Course, ordered_sections: list[Section], is_complete: Callable[[Section], bool]) -> Section | None:
    """Return the first incomplete progression gate before any requested section."""
    if course.progression_mode is ProgressionMode.FREE:
        return None
    for section in ordered_sections:
        if section.status.value != "PUBLISHED":
            continue
        if not is_complete(section):
            return section
    return None


def require_sequential_access(course: Course, ordered_sections: list[Section], target: Section, is_complete: Callable[[Section], bool]) -> None:
    """Reject a target while any preceding sequential gate remains incomplete."""
    if course.progression_mode is ProgressionMode.FREE:
        return
    preceding: list[Section] = []
    for section in ordered_sections:
        if section.id == target.id:
            blocker = first_blocking_section(course, preceding, is_complete)
            if blocker is not None:
                raise ValidationError(f"section is locked until '{blocker.title}' is complete")
            return
        preceding.append(section)
    raise ValidationError("section does not belong to the course")
