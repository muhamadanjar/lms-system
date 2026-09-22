from app.domain.entities.course import Course
from app.domain.entities.module import Module
from app.infrastructure.persistence.unit_of_work import SqlModelUnitOfWork


async def test_repository_contract_rejects_missing_parent(session):
    module = Module(slug="orphan-module", course_id=__import__("uuid").uuid4(), title="Orphan")
    async with SqlModelUnitOfWork(session=session) as uow:
        try:
            await uow.modules.create(module)
        except Exception as exc:
            assert "course" in str(exc).lower()
        else:
            raise AssertionError("orphan module was persisted")


async def test_course_repository_can_load_by_slug(session):
    course = Course(slug="contract-course", title="Contract")
    async with SqlModelUnitOfWork(session=session) as uow:
        await uow.courses.create(course)
        await uow.commit()
    async with SqlModelUnitOfWork(session=session) as uow:
        loaded = await uow.courses.get_by_slug("contract-course")
        await uow.rollback()
    assert loaded is not None
    assert loaded.id == course.id
