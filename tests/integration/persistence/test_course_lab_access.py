from uuid import uuid4

import pytest

from app.domain.entities.course_lab_access import CourseLabAccess
from app.domain.exceptions import ConflictError
from app.infrastructure.persistence.models.course import Course
from app.infrastructure.persistence.models.remote_server import RemoteServer
from app.infrastructure.persistence.repositories.course_lab_access_repository import SqlModelCourseLabAccessRepository
from app.infrastructure.persistence.unit_of_work import SqlModelUnitOfWork


async def _course(session):
    course = Course(slug=f"c-{uuid4().hex[:8]}", title="C", sequence=0)
    session.add(course)
    await session.flush()
    return course


async def _server(session, name=None):
    server = RemoteServer(name=name or f"srv-{uuid4().hex[:8]}", host="10.0.0.9", username="u")
    session.add(server)
    await session.flush()
    return server


def _uow(session):
    return SqlModelUnitOfWork(session=session)


async def test_create_and_get_live(session):
    course = await _course(session)
    server = await _server(session)
    async with _uow(session) as uow:
        repo = SqlModelCourseLabAccessRepository(session)
        created = await repo.create(CourseLabAccess(user_id="u1", course_id=course.id, server_id=server.id))
        await uow.commit()
        live = await repo.get_live("u1", course.id)
        assert live is not None and live.id == created.id


async def test_duplicate_live_user_course_conflicts(session):
    course = await _course(session)
    s1 = await _server(session)
    s2 = await _server(session)
    repo = SqlModelCourseLabAccessRepository(session)
    await repo.create(CourseLabAccess(user_id="u1", course_id=course.id, server_id=s1.id))
    with pytest.raises(ConflictError):
        await repo.create(CourseLabAccess(user_id="u1", course_id=course.id, server_id=s2.id))


async def test_server_exclusivity_across_users(session):
    c1 = await _course(session)
    c2 = await _course(session)
    server = await _server(session)
    repo = SqlModelCourseLabAccessRepository(session)
    await repo.create(CourseLabAccess(user_id="u1", course_id=c1.id, server_id=server.id))
    with pytest.raises(ConflictError):
        await repo.create(CourseLabAccess(user_id="u2", course_id=c2.id, server_id=server.id))


async def test_release_allows_reuse(session):
    course = await _course(session)
    server = await _server(session)
    repo = SqlModelCourseLabAccessRepository(session)
    access = await repo.create(CourseLabAccess(user_id="u1", course_id=course.id, server_id=server.id))
    access.release()
    await repo.update(access)
    reused = await repo.create(CourseLabAccess(user_id="u2", course_id=course.id, server_id=server.id))
    assert reused.server_id == server.id
    assert await repo.get_live("u1", course.id) is None


async def test_free_server_ids_skips_taken(session):
    course = await _course(session)
    s1 = await _server(session)
    s2 = await _server(session)
    repo = SqlModelCourseLabAccessRepository(session)
    await repo.create(CourseLabAccess(user_id="u1", course_id=course.id, server_id=s1.id))
    free = await repo.free_server_ids(5)
    assert s1.id not in free and s2.id in free
