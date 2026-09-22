from collections.abc import Iterable
from uuid import UUID

from app.domain.entities.course import Course
from app.domain.entities.module import Module
from app.domain.entities.section import CourseHierarchy, Section
from app.domain.services.content_ordering import reorder_positions, validate_unique_positions


class ContentHierarchyUseCases:
    def __init__(self, uow_factory):
        self.uow_factory = uow_factory

    async def create(self, course: Course, modules: Iterable[Module], sections: Iterable[Section]) -> CourseHierarchy:
        modules = list(modules)
        sections = list(sections)
        validate_unique_positions(modules)
        sections_by_module = {}
        for section in sections:
            sections_by_module.setdefault(section.module_id, []).append(section)
        for siblings in sections_by_module.values():
            validate_unique_positions(siblings)
        async with self.uow_factory() as uow:
            await uow.courses.create(course)
            for module in modules:
                await uow.modules.create(module)
            for section in sections:
                await uow.sections.create(section)
            await uow.commit()
        return await self.load(course.id)

    async def load(self, course_id: UUID, include_archived: bool = False) -> CourseHierarchy:
        async with self.uow_factory() as uow:
            hierarchy = await uow.courses.get_hierarchy(course_id, include_archived=include_archived)
            await uow.rollback()
        if hierarchy is None:
            raise LookupError("course not found")
        return hierarchy

    async def reorder_modules(self, course_id: UUID, ordered_module_ids: list[UUID]) -> None:
        async with self.uow_factory() as uow:
            await uow.modules.reorder(course_id, ordered_module_ids)
            await uow.commit()

    async def reorder_sections(self, module_id: UUID, ordered_section_ids: list[UUID]) -> None:
        async with self.uow_factory() as uow:
            await uow.sections.reorder(module_id, ordered_section_ids)
            await uow.commit()

    async def delete_course(self, course_id: UUID) -> bool:
        async with self.uow_factory() as uow:
            deleted = await uow.courses.delete(course_id)
            await uow.commit()
            return deleted


async def create_hierarchy(uow, course: Course, modules: Iterable[Module], sections: Iterable[Section]) -> CourseHierarchy:
    """Small functional entry point useful for application tests and adapters."""
    use_cases = ContentHierarchyUseCases(lambda: uow)
    return await use_cases.create(course, modules, sections)
