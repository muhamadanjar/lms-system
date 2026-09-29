"""Enrollment use-cases with fake ports (TDD)."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.application.use_cases.enrollment import EnrollmentUseCases
from app.domain.entities.enrollment import Enrollment
from app.domain.exceptions import ConflictError, NotFoundError


class FakeCourse:
    def __init__(self, slug):
        self.id = uuid4()
        self.slug = slug


class FakeCourses:
    def __init__(self, courses):
        self.by_slug = {c.slug: c for c in courses}

    async def get_by_slug(self, slug):
        return self.by_slug.get(slug)


class FakeEnrollmentRepo:
    def __init__(self):
        self.rows: dict[str, Enrollment] = {}

    def _live_key(self, user_id, course_id):
        return next((k for k, r in self.rows.items() if r.user_id == user_id and str(r.course_id) == str(course_id) and r.status == "ENROLLED"), None)

    async def get_live(self, user_id, course_id):
        key = self._live_key(user_id, course_id)
        return self.rows.get(key) if key else None

    async def create(self, enrollment):
        if self._live_key(enrollment.user_id, enrollment.course_id):
            raise ConflictError("duplicate live enrollment")
        self.rows[str(enrollment.id)] = enrollment
        return enrollment

    async def update(self, enrollment):
        self.rows[str(enrollment.id)] = enrollment
        return enrollment

    async def list_live_by_course(self, course_id):
        return [r for r in self.rows.values() if str(r.course_id) == str(course_id) and r.status == "ENROLLED"]

    async def list_history(self, user_id, course_id):
        return [r for r in self.rows.values() if r.user_id == user_id and str(r.course_id) == str(course_id)]


class FakeLabAccess:
    def __init__(self):
        self.released: list = []

    async def get_live(self, user_id, course_id):
        return None


class FakeUoW:
    def __init__(self, courses, enrollments, lab_access=None):
        self.courses = FakeCourses(courses)
        self.enrollments = enrollments
        self.lab_access = lab_access or FakeLabAccess()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def commit(self):
        return None

    async def rollback(self):
        return None


def make_uc(slugs=("c1",)):
    courses = [FakeCourse(s) for s in slugs]
    repo = FakeEnrollmentRepo()
    uow = FakeUoW(courses, repo)
    return EnrollmentUseCases(lambda: uow), repo


async def test_enroll_creates_live_record():
    uc, _ = make_uc()
    enrollment = await uc.enroll("c1", "u1")
    assert enrollment.status == "ENROLLED"
    assert enrollment.enrolled_at.tzinfo is not None


async def test_reenroll_returns_existing():
    uc, repo = make_uc()
    first = await uc.enroll("c1", "u1")
    second = await uc.enroll("c1", "u1")
    assert first.id == second.id
    assert len(repo.rows) == 1


async def test_enroll_with_backdate():
    uc, _ = make_uc()
    when = datetime(2026, 1, 5, tzinfo=timezone.utc)
    enrollment = await uc.enroll("c1", "u1", enrolled_at=when)
    assert enrollment.enrolled_at == when


async def test_enroll_unknown_course():
    uc, _ = make_uc()
    with pytest.raises(NotFoundError):
        await uc.enroll("missing", "u1")


async def test_complete_stamps_completed_at():
    uc, _ = make_uc()
    await uc.enroll("c1", "u1")
    done = await uc.complete("c1", "u1")
    assert done.status == "COMPLETED"
    assert done.completed_at is not None


async def test_complete_without_enrollment_raises():
    uc, _ = make_uc()
    with pytest.raises(NotFoundError):
        await uc.complete("c1", "ghost")


async def test_withdraw_and_reenroll_creates_new_row():
    uc, repo = make_uc()
    await uc.enroll("c1", "u1")
    withdrawn = await uc.withdraw("c1", "u1")
    assert withdrawn.status == "WITHDRAWN"
    second = await uc.enroll("c1", "u1")
    assert second.id != withdrawn.id
    assert len(repo.rows) == 2
