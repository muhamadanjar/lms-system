from uuid import uuid4

import pytest

from app.domain.entities.course_lab_access import CourseLabAccess, CourseLabAccessState
from app.domain.exceptions import ValidationError


def test_active_requires_server():
    with pytest.raises(ValidationError):
        CourseLabAccess(user_id="u1", course_id=uuid4(), server_id=None, state=CourseLabAccessState.ACTIVE)


def test_released_must_not_hold_server():
    with pytest.raises(ValidationError):
        CourseLabAccess(user_id="u1", course_id=uuid4(), server_id=uuid4(), state=CourseLabAccessState.RELEASED)


def test_user_and_course_required():
    with pytest.raises(ValidationError):
        CourseLabAccess(user_id="  ", course_id=uuid4(), server_id=uuid4())
    with pytest.raises(ValidationError):
        CourseLabAccess(user_id="u1", course_id=None, server_id=uuid4())


def test_release_clears_server_and_is_terminal():
    access = CourseLabAccess(user_id="u1", course_id=uuid4(), server_id=uuid4())
    access.release()
    assert access.state == CourseLabAccessState.RELEASED
    assert access.server_id is None
    with pytest.raises(ValidationError):
        access.release()


def test_unknown_state_rejected():
    with pytest.raises(ValidationError):
        CourseLabAccess(user_id="u1", course_id=uuid4(), server_id=uuid4(), state="QUEUED")
