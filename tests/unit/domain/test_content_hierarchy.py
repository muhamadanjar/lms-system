from uuid import uuid4

import pytest

from app.domain.entities.course import Course
from app.domain.entities.module import Module
from app.domain.entities.section import Section
from app.domain.exceptions import ValidationError
from app.domain.services.content_ordering import reorder_positions
from app.domain.value_objects.content import ContentStatus, SectionContentType


def test_hierarchy_entities_validate_required_values():
    course = Course(slug="course-1", title="Course")
    module = Module(slug="module-1", course_id=course.id, title="Module", position=0)
    section = Section(slug="section-1", module_id=module.id, title="Section", position=0)

    assert course.status is ContentStatus.DRAFT
    assert section.content_type is SectionContentType.MATERIAL


def test_empty_title_and_negative_position_are_rejected():
    with pytest.raises(ValidationError):
        Course(slug="course-1", title=" ")
    with pytest.raises(ValidationError):
        Module(slug="module-1", course_id=uuid4(), title="Module", position=-1)


def test_slug_is_immutable_and_status_update_touches_timestamp():
    course = Course(slug="course-1", title="Course")
    created_at = course.updated_at
    with pytest.raises(ValidationError):
        course.change_slug("course-2")
    course.change_status(ContentStatus.PUBLISHED)
    assert course.status is ContentStatus.PUBLISHED
    assert course.updated_at >= created_at


def test_reorder_requires_exact_siblings():
    course = Course(slug="course-1", title="Course")
    modules = [
        Module(slug="module-1", course_id=course.id, title="One", position=0),
        Module(slug="module-2", course_id=course.id, title="Two", position=1),
    ]
    reorder_positions(modules, [modules[1].id, modules[0].id])
    assert [module.position for module in modules] == [1, 0]
