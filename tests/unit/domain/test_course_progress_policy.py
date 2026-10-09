from uuid import uuid4

import pytest

from app.domain.entities.course import Course
from app.domain.entities.section import Section
from app.domain.exceptions import ValidationError
from app.domain.services.learning_progression import require_sequential_access
from app.domain.value_objects.content import ContentStatus, SectionContentType
from app.domain.value_objects.learning_policy import CompletionMode, ProgressionMode


def test_course_policy_defaults_and_normalizes_enums():
    course = Course(title="Intro", slug="intro")
    assert course.progression_mode is ProgressionMode.FREE
    assert course.completion_mode is CompletionMode.SELF_LEARNING


def test_sequential_course_locks_later_material_until_previous_complete():
    course = Course(title="Intro", slug="intro", progression_mode=ProgressionMode.SEQUENTIAL)
    first = Section(module_id=uuid4(), title="First", slug="first", position=0, status=ContentStatus.PUBLISHED)
    later = Section(module_id=first.module_id, title="Later", slug="later", position=1, status=ContentStatus.PUBLISHED)

    with pytest.raises(ValidationError, match="First"):
        require_sequential_access(course, [first, later], later, lambda _: False)

    require_sequential_access(course, [first, later], later, lambda _: True)


def test_free_course_does_not_lock_and_submitted_lab_gate_can_unlock_next_section():
    course = Course(title="Intro", slug="intro", progression_mode="FREE")
    lab = Section(module_id=uuid4(), title="Lab", slug="lab", content_type=SectionContentType.LAB_TASK, status=ContentStatus.PUBLISHED)
    next_section = Section(module_id=lab.module_id, title="Next", slug="next", position=1, status=ContentStatus.PUBLISHED)
    require_sequential_access(course, [lab, next_section], next_section, lambda _: False)

    course.progression_mode = ProgressionMode.SEQUENTIAL
    with pytest.raises(ValidationError, match="Lab"):
        require_sequential_access(course, [lab, next_section], next_section, lambda _: False)
    require_sequential_access(course, [lab, next_section], next_section, lambda _: True)
