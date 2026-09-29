"""Course-scoped lab enrollment with fake ports (TDD)."""

from uuid import uuid4

import pytest

from app.application.use_cases.lab_enrollment import LabEnrollmentUseCases
from app.domain.entities.course_lab_access import CourseLabAccess
from app.domain.exceptions import AuthorizationError, ConflictError, NotFoundError


class FakeEnrollments:
    """Semua user dianggap ENROLLED kecuali yang didaftarkan di denied."""

    def __init__(self):
        self.denied: set[tuple[str, str]] = set()

    async def get_live(self, user_id, course_id):
        if (user_id, str(course_id)) in self.denied:
            return None
        return object()


class FakeCourse:
    def __init__(self, slug):
        self.id = uuid4()
        self.slug = slug


class FakeCourses:
    def __init__(self, courses):
        self.by_slug = {c.slug: c for c in courses}

    async def get_by_slug(self, slug):
        return self.by_slug.get(slug)


class FakeLabAccessRepo:
    def __init__(self, servers):
        self.servers = list(servers)
        self.rows: dict[tuple[str, str], CourseLabAccess] = {}

    async def get_live(self, user_id, course_id):
        return self.rows.get((user_id, str(course_id)))

    async def create(self, access):
        key = (access.user_id, str(access.course_id))
        if key in self.rows:
            raise ConflictError("duplicate live course lab access")
        if any(r.server_id == access.server_id for r in self.rows.values()):
            raise ConflictError("duplicate live course lab access")
        self.rows[key] = access
        return access

    async def update(self, access):
        key = (access.user_id, str(access.course_id))
        if key not in self.rows:
            raise NotFoundError("course lab access not found")
        self.rows[key] = access
        return access

    async def list_live_by_user(self, user_id):
        return [r for (u, _), r in self.rows.items() if u == user_id]

    async def list_live_by_course(self, course_id):
        return [r for (_, c), r in self.rows.items() if c == str(course_id)]

    async def free_server_ids(self, limit):
        taken = {r.server_id for r in self.rows.values()}
        return [s for s in self.servers if s not in taken][:limit]

    async def find_active_by_server(self, server_id):
        return next((r for r in self.rows.values() if r.server_id == server_id), None)


class FakeUoW:
    def __init__(self, courses, repo, enrollments=None):
        self.courses = FakeCourses(courses)
        self.lab_access = repo
        self.enrollments = enrollments or FakeEnrollments()
        self.commits = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        return None


def make_uc(slugs=("c1",), servers=2):
    courses = [FakeCourse(s) for s in slugs]
    repo = FakeLabAccessRepo([uuid4() for _ in range(servers)])
    uow = FakeUoW(courses, repo)
    return LabEnrollmentUseCases(lambda: uow), repo


async def test_enroll_returns_one_access_per_course():
    uc, _ = make_uc()
    access = await uc.enroll("c1", "u1")
    assert access.user_id == "u1"
    assert access.server_id is not None


async def test_reenroll_returns_existing_without_duplicate():
    uc, repo = make_uc()
    first = await uc.enroll("c1", "u1")
    second = await uc.enroll("c1", "u1")
    assert first.id == second.id
    assert len(repo.rows) == 1


async def test_different_courses_get_different_servers():
    uc, _ = make_uc(slugs=("c1", "c2"), servers=2)
    a1 = await uc.enroll("c1", "u1")
    a2 = await uc.enroll("c2", "u1")
    assert a1.server_id != a2.server_id


async def test_capacity_failure_leaves_no_row():
    uc, repo = make_uc(servers=0)
    with pytest.raises(ConflictError):
        await uc.enroll("c1", "u1")
    assert repo.rows == {}


async def test_release_frees_server_for_next_learner():
    uc, _ = make_uc(servers=1)
    await uc.enroll("c1", "u1")
    released = await uc.release("c1", "u1")
    assert released.state == "RELEASED"
    second = await uc.enroll("c1", "u2")
    assert second.server_id is not None


async def test_release_without_access_raises_not_found():
    uc, _ = make_uc()
    with pytest.raises(NotFoundError):
        await uc.release("c1", "ghost")


async def test_unknown_course_raises_not_found():
    uc, _ = make_uc()
    with pytest.raises(NotFoundError):
        await uc.enroll("missing", "u1")


async def test_lab_enroll_denied_without_enrollment():
    courses = [FakeCourse("c1")]
    repo = FakeLabAccessRepo([uuid4()])
    denied = FakeEnrollments()
    denied.denied.add(("luar", str(courses[0].id)))
    uc = LabEnrollmentUseCases(lambda: FakeUoW(courses, repo, denied))
    with pytest.raises(AuthorizationError):
        await uc.enroll("c1", "luar")
    assert repo.rows == {}
