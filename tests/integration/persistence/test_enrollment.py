from uuid import uuid4

import pytest

from app.domain.entities.enrollment import Enrollment
from app.domain.exceptions import ConflictError
from app.infrastructure.persistence.models.course import Course
from app.infrastructure.persistence.models.enrollment import Enrollment as EnrollmentRow
from app.infrastructure.persistence.repositories.enrollment_repository import SqlModelEnrollmentRepository
from app.infrastructure.persistence.unit_of_work import SqlModelUnitOfWork


async def _course(session):
    course = Course(slug=f"enr-{uuid4().hex[:8]}", title="C", sequence=0)
    session.add(course)
    await session.flush()
    return course


async def test_create_and_get_live(session):
    course = await _course(session)
    repo = SqlModelEnrollmentRepository(session)
    created = await repo.create(Enrollment(user_id="u1", course_id=course.id))
    live = await repo.get_live("u1", course.id)
    assert live is not None and live.id == created.id
    assert live.enrolled_at.tzinfo is not None


async def test_duplicate_live_conflicts_but_history_coexists(session):
    course = await _course(session)
    repo = SqlModelEnrollmentRepository(session)
    first = await repo.create(Enrollment(user_id="u1", course_id=course.id))
    await session.commit()
    with pytest.raises(ConflictError):
        await repo.create(Enrollment(user_id="u1", course_id=course.id))
    await session.rollback()
    first.withdraw()
    await repo.update(first)
    second = await repo.create(Enrollment(user_id="u1", course_id=course.id))
    assert second.id != first.id
    history = await repo.list_history("u1", course.id)
    assert {r.status for r in history} == {"WITHDRAWN", "ENROLLED"}


async def test_course_delete_cascades_enrollments(session):
    course = await _course(session)
    repo = SqlModelEnrollmentRepository(session)
    await repo.create(Enrollment(user_id="u1", course_id=course.id))
    async with SqlModelUnitOfWork(session=session) as uow:
        assert await uow.courses.delete(course.id) is True
        await uow.commit()
    assert await repo.get_live("u1", course.id) is None


async def test_list_live_by_course(session):
    course = await _course(session)
    repo = SqlModelEnrollmentRepository(session)
    await repo.create(Enrollment(user_id="u1", course_id=course.id))
    withdrawn = await repo.create(Enrollment(user_id="u2", course_id=course.id))
    withdrawn.withdraw()
    await repo.update(withdrawn)
    live = await repo.list_live_by_course(course.id)
    assert [r.user_id for r in live] == ["u1"]
    assert EnrollmentRow.__tablename__ == "enrollments"
