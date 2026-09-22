from sqlmodel import select

from app.domain.entities.course import Course
from app.domain.entities.module import Module
from app.domain.entities.section import Section
from app.infrastructure.persistence.models.content_slug_registry import ContentSlugRegistry
from app.infrastructure.persistence.models.course import Course as CourseRow
from app.infrastructure.persistence.models.module import Module as ModuleRow
from app.infrastructure.persistence.models.section import Section as SectionRow
from app.infrastructure.persistence.unit_of_work import SqlModelUnitOfWork
from app.application.use_cases.content_hierarchy import ContentHierarchyUseCases


async def test_reorder_and_delete_are_atomic(session):
    course = Course(slug="ordered-course", title="Ordered")
    module = Module(slug="ordered-module", course_id=course.id, title="Module", position=0)
    first = Section(slug="first", module_id=module.id, title="First", position=0)
    second = Section(slug="second", module_id=module.id, title="Second", position=1)
    use_cases = ContentHierarchyUseCases(lambda: SqlModelUnitOfWork(session=session))
    await use_cases.create(course, [module], [first, second])

    await use_cases.reorder_sections(module.id, [second.id, first.id])
    ordered = await use_cases.load(course.id)
    assert [section.id for section in ordered.sections_by_module[module.id]] == [second.id, first.id]

    assert await use_cases.delete_course(course.id) is True
    assert (await session.exec(select(CourseRow))).all() == []
    assert (await session.exec(select(ModuleRow))).all() == []
    assert (await session.exec(select(SectionRow))).all() == []
    assert (await session.exec(select(ContentSlugRegistry))).all() == []
