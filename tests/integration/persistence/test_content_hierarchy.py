from app.application.use_cases.content_hierarchy import ContentHierarchyUseCases
from app.domain.entities.course import Course
from app.domain.entities.module import Module
from app.domain.entities.section import Section
from app.infrastructure.persistence.unit_of_work import SqlModelUnitOfWork


async def test_create_and_load_ordered_hierarchy(session):
    course = Course(slug="python-course", title="Python Course")
    first = Module(slug="python-basics", course_id=course.id, title="Basics", position=0)
    second = Module(slug="python-advanced", course_id=course.id, title="Advanced", position=1)
    sections = [
        Section(slug="variables", module_id=first.id, title="Variables", position=1),
        Section(slug="syntax", module_id=first.id, title="Syntax", position=0),
        Section(slug="async", module_id=second.id, title="Async", position=0),
    ]
    use_cases = ContentHierarchyUseCases(lambda: SqlModelUnitOfWork(session=session))

    hierarchy = await use_cases.create(course, [first, second], sections)
    loaded = await use_cases.load(course.id)

    assert hierarchy.course.id == loaded.course.id == course.id
    assert [module.slug for module in loaded.modules] == ["python-basics", "python-advanced"]
    assert [section.slug for section in loaded.sections_by_module[first.id]] == ["syntax", "variables"]
    assert [section.module_id for section in loaded.sections_by_module[second.id]] == [second.id]
