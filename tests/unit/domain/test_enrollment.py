from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.domain.entities.enrollment import Enrollment, EnrollmentStatus
from app.domain.exceptions import ValidationError


def _now():
    return datetime.now(timezone.utc)


def test_default_is_enrolled_without_completed_at():
    enrollment = Enrollment(user_id="u1", course_id=uuid4())
    assert enrollment.status == EnrollmentStatus.ENROLLED
    assert enrollment.completed_at is None
    assert enrollment.enrolled_at.tzinfo is not None


def test_user_and_course_required():
    with pytest.raises(ValidationError):
        Enrollment(user_id="  ", course_id=uuid4())
    with pytest.raises(ValidationError):
        Enrollment(user_id="u1", course_id=None)


def test_completed_requires_completed_at():
    with pytest.raises(ValidationError):
        Enrollment(user_id="u1", course_id=uuid4(), status=EnrollmentStatus.COMPLETED)


def test_non_completed_must_not_hold_completed_at():
    with pytest.raises(ValidationError):
        Enrollment(user_id="u1", course_id=uuid4(), status=EnrollmentStatus.ENROLLED, completed_at=_now())
    with pytest.raises(ValidationError):
        Enrollment(user_id="u1", course_id=uuid4(), status=EnrollmentStatus.WITHDRAWN, completed_at=_now())


def test_complete_stamps_and_is_terminal():
    enrollment = Enrollment(user_id="u1", course_id=uuid4())
    enrollment.complete()
    assert enrollment.status == EnrollmentStatus.COMPLETED
    assert enrollment.completed_at is not None
    with pytest.raises(ValidationError):
        enrollment.complete()
    with pytest.raises(ValidationError):
        enrollment.withdraw()


def test_withdraw_is_terminal():
    enrollment = Enrollment(user_id="u1", course_id=uuid4())
    enrollment.withdraw()
    assert enrollment.status == EnrollmentStatus.WITHDRAWN
    with pytest.raises(ValidationError):
        enrollment.withdraw()


def test_naive_datetimes_rejected():
    naive = datetime.now()
    with pytest.raises(ValidationError):
        Enrollment(user_id="u1", course_id=uuid4(), enrolled_at=naive)
