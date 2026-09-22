import pytest
from sqlalchemy.exc import IntegrityError

from app.domain.entities.course import Course
from app.domain.entities.module import Module
from app.infrastructure.persistence.unit_of_work import SqlModelUnitOfWork


async def test_duplicate_sibling_positions_fail_without_partial_commit(session):
    course = Course(slug="position-course", title="Positions")
    first = Module(slug="position-one", course_id=course.id, title="One", position=0)
    second = Module(slug="position-two", course_id=course.id, title="Two", position=0)
    async with SqlModelUnitOfWork(session=session) as uow:
        await uow.courses.create(course)
        await uow.modules.create(first)
        with pytest.raises(IntegrityError):
            await uow.modules.create(second)
    async with SqlModelUnitOfWork(session=session) as uow:
        assert len(await uow.modules.list_by_course(course.id, include_archived=True)) == 0
        await uow.rollback()
