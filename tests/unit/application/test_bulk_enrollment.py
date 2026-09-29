"""Bulk enrollment with fake directory (TDD)."""

from uuid import uuid4

import pytest

from app.application.ports.user_directory import DirectoryUnavailable, EmailAmbiguous, EmailNotFound
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

    def _live(self, user_id, course_id):
        return next((r for r in self.rows.values() if r.user_id == user_id and str(r.course_id) == str(course_id) and r.status == "ENROLLED"), None)

    async def get_live(self, user_id, course_id):
        return self._live(user_id, course_id)

    async def create(self, enrollment):
        if self._live(enrollment.user_id, enrollment.course_id):
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
    async def get_live(self, user_id, course_id):
        return None


class FakeDirectory:
    def __init__(self, mapping=None, down=False, ambiguous=()):
        self.mapping = mapping or {}
        self.down = down
        self.ambiguous = set(ambiguous)
        self.calls: list[str] = []

    async def find_user_id_by_email(self, email, authorization):
        self.calls.append(email)
        if self.down:
            raise DirectoryUnavailable("down")
        lowered = {k.lower(): v for k, v in self.mapping.items()}
        if email.lower() in {a.lower() for a in self.ambiguous}:
            raise EmailAmbiguous(email)
        if email.lower() not in lowered:
            raise EmailNotFound(email)
        return lowered[email.lower()]


class FakeUoW:
    def __init__(self, courses, enrollments):
        self.courses = FakeCourses(courses)
        self.enrollments = enrollments
        self.lab_access = FakeLabAccess()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def commit(self):
        return None

    async def rollback(self):
        return None


def make_uc(slugs=("c1",), directory=None):
    courses = [FakeCourse(s) for s in slugs]
    repo = FakeEnrollmentRepo()
    uow = FakeUoW(courses, repo)
    return EnrollmentUseCases(lambda: uow, user_directory=directory or FakeDirectory()), repo


async def test_bulk_mixed_new_existing_invalid():
    uc, repo = make_uc()
    await uc.enroll("c1", "existing")
    result = await uc.bulk_enroll("c1", [{"user_id": "u1"}, {"user_id": "existing"}, {"user_id": "  "}, {}])
    assert [e.user_id for e in result.enrolled] == ["u1"]
    assert result.skipped == [{"identifier": "existing", "reason": "already_enrolled"}]
    assert [f["reason"] for f in result.failed] == ["INVALID", "INVALID"]
    assert len(repo.rows) == 2


async def test_bulk_dedup_within_request():
    uc, repo = make_uc()
    result = await uc.bulk_enroll("c1", [{"user_id": "u1"}, {"user_id": "u1"}])
    assert len(result.enrolled) == 1
    assert result.skipped == [{"identifier": "u1", "reason": "duplicate_in_request"}]
    assert len(repo.rows) == 1


async def test_bulk_unknown_course():
    uc, _ = make_uc()
    with pytest.raises(NotFoundError):
        await uc.bulk_enroll("missing", [{"user_id": "u1"}])


async def test_bulk_email_resolved_to_canonical_id():
    directory = FakeDirectory(mapping={"A@x.id": "u-9"})
    uc, repo = make_uc(directory=directory)
    result = await uc.bulk_enroll("c1", [{"email": "a@X.id"}], authorization="Bearer t")
    assert [e.user_id for e in result.enrolled] == ["u-9"]
    assert directory.calls == ["a@X.id"]


async def test_bulk_email_not_found_and_ambiguous():
    directory = FakeDirectory(mapping={}, ambiguous=("dup@x.id",))
    uc, _ = make_uc(directory=directory)
    result = await uc.bulk_enroll("c1", [{"email": "ghost@x.id"}, {"email": "dup@x.id"}, {"user_id": "u1"}])
    assert result.enrolled[0].user_id == "u1"
    assert {f["identifier"]: f["reason"] for f in result.failed} == {"ghost@x.id": "NOT_FOUND", "dup@x.id": "AMBIGUOUS"}


async def test_bulk_directory_down_fails_only_email_items():
    uc, _ = make_uc(directory=FakeDirectory(down=True))
    result = await uc.bulk_enroll("c1", [{"email": "a@x.id"}, {"user_id": "u1"}])
    assert [e.user_id for e in result.enrolled] == ["u1"]
    assert result.failed == [{"identifier": "a@x.id", "reason": "DIRECTORY_UNAVAILABLE"}]


async def test_bulk_user_id_wins_over_email():
    directory = FakeDirectory(mapping={"a@x.id": "u-other"})
    uc, _ = make_uc(directory=directory)
    result = await uc.bulk_enroll("c1", [{"user_id": "u1", "email": "a@x.id"}])
    assert [e.user_id for e in result.enrolled] == ["u1"]
    assert directory.calls == []
