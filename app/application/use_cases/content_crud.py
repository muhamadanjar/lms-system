from collections.abc import Callable
from typing import Any
from uuid import UUID

from app.domain.entities.course import Course
from app.domain.entities.module import Module
from app.domain.entities.section import Section
from app.domain.entities.quiz import KnowledgeQuiz
from app.domain.exceptions import NotFoundError, ValidationError
from app.domain.services.content_policy import validate_status_transition
from app.domain.value_objects.content import ContentStatus, SectionContentType, Slug


class ContentCrudUseCases:
    def __init__(self, uow_factory: Callable):
        self.uow_factory = uow_factory

    async def list_courses(self, status: ContentStatus | None, include_archived: bool, offset: int, limit: int):
        async with self.uow_factory() as uow:
            courses = await uow.courses.list(status.value if status else None, include_archived, offset, limit)
            total = await uow.courses.count(status.value if status else None, include_archived)
            await uow.rollback()
            return courses, total

    async def create_course(self, course: Course) -> Course:
        async with self.uow_factory() as uow:
            result = await uow.courses.create(course)
            await uow.commit()
            return result

    async def get_course(self, slug: str, include_archived: bool = False):
        async with self.uow_factory() as uow:
            course = await uow.courses.get_by_slug(slug)
            if course is None:
                raise NotFoundError("course not found")
            hierarchy = await uow.courses.get_hierarchy(course.id, include_archived=include_archived)
            await uow.rollback()
            return hierarchy

    async def update_course(self, slug: str, changes: dict[str, Any]) -> Course:
        async with self.uow_factory() as uow:
            course = await uow.courses.get_by_slug(slug)
            if course is None:
                raise NotFoundError("course not found")
            _apply_common_changes(course, changes)
            if "progression_mode" in changes:
                from app.domain.value_objects.learning_policy import ProgressionMode
                course.progression_mode = ProgressionMode(changes["progression_mode"])
            if "completion_mode" in changes:
                from app.domain.value_objects.learning_policy import CompletionMode
                course.completion_mode = CompletionMode(changes["completion_mode"])
            result = await uow.courses.update(course)
            await uow.commit()
            return result

    async def delete_course(self, slug: str) -> bool:
        async with self.uow_factory() as uow:
            course = await uow.courses.get_by_slug(slug)
            if course is None:
                raise NotFoundError("course not found")
            deleted = await uow.courses.delete(course.id)
            await uow.commit()
            return deleted

    async def list_modules(self, course_slug: str, status: ContentStatus | None, include_archived: bool, offset: int = 0, limit: int = 20):
        async with self.uow_factory() as uow:
            course = await uow.courses.get_by_slug(course_slug)
            if course is None:
                raise NotFoundError("course not found")
            modules = list(await uow.modules.list_by_course(course.id, include_archived=include_archived, offset=offset, limit=limit))
            total = await uow.modules.count_by_course(course.id, include_archived=include_archived)
            if status:
                modules = [module for module in modules if module.status is status]
            await uow.rollback()
            return modules, total, course

    async def create_module(self, course_slug: str, *, title: str, description: str | None, slug: str, position: int, status: ContentStatus) -> Module:
        async with self.uow_factory() as uow:
            course = await uow.courses.get_by_slug(course_slug)
            if course is None:
                raise NotFoundError("course not found")
            module = Module(course_id=course.id, title=title, description=description, slug=Slug(slug), position=position, status=status)
            result = await uow.modules.create(module)
            await uow.commit()
            return result

    async def get_module(self, course_slug: str, module_slug: str, include_archived: bool):
        async with self.uow_factory() as uow:
            course = await uow.courses.get_by_slug(course_slug)
            if course is None:
                raise NotFoundError("course not found")
            module = await uow.modules.get_by_slug(course.id, module_slug)
            if module is None or (not include_archived and module.status is ContentStatus.ARCHIVED):
                raise NotFoundError("module not found")
            sections = list(await uow.sections.list_by_module(module.id, include_archived=include_archived, offset=0, limit=100000))
            await uow.rollback()
            return course, module, sections

    async def update_module(self, course_slug: str, module_slug: str, changes: dict[str, Any]) -> Module:
        async with self.uow_factory() as uow:
            course = await uow.courses.get_by_slug(course_slug)
            if course is None:
                raise NotFoundError("course not found")
            module = await uow.modules.get_by_slug(course.id, module_slug)
            if module is None:
                raise NotFoundError("module not found")
            _apply_common_changes(module, changes)
            if "position" in changes:
                raise ValidationError("position must be changed through the order endpoint")
            result = await uow.modules.update(module)
            await uow.commit()
            return result

    async def delete_module(self, course_slug: str, module_slug: str) -> bool:
        async with self.uow_factory() as uow:
            course = await uow.courses.get_by_slug(course_slug)
            if course is None:
                raise NotFoundError("course not found")
            module = await uow.modules.get_by_slug(course.id, module_slug)
            if module is None:
                raise NotFoundError("module not found")
            result = await uow.modules.delete(module.id)
            await uow.commit()
            return result

    async def list_sections(self, course_slug: str, module_slug: str, status: ContentStatus | None, include_archived: bool, offset: int = 0, limit: int = 20):
        async with self.uow_factory() as uow:
            course = await uow.courses.get_by_slug(course_slug)
            if course is None:
                raise NotFoundError("course not found")
            module = await uow.modules.get_by_slug(course.id, module_slug)
            if module is None or (not include_archived and module.status is ContentStatus.ARCHIVED):
                raise NotFoundError("module not found")
            sections = list(await uow.sections.list_by_module(module.id, include_archived=include_archived, offset=offset, limit=limit))
            total = await uow.sections.count_by_module(module.id, include_archived=include_archived)
            await uow.rollback()
        if status:
            sections = [section for section in sections if section.status is status]
        return sections, total, course, module

    async def create_section(self, course_slug: str, module_slug: str, *, title: str, description: str | None, slug: str, position: int, status: ContentStatus, content_type: SectionContentType, body: str | None, requires_pass: bool = False, is_preview: bool = False, terminal_enabled: bool = False) -> Section:
        async with self.uow_factory() as uow:
            course = await uow.courses.get_by_slug(course_slug)
            if course is None:
                raise NotFoundError("course not found")
            module = await uow.modules.get_by_slug(course.id, module_slug)
            if module is None:
                raise NotFoundError("module not found")
            section = Section(module_id=module.id, title=title, description=description, slug=Slug(slug), position=position, status=status, content_type=content_type, body=body, requires_pass=requires_pass, is_preview=is_preview, terminal_enabled=terminal_enabled)
            result = await uow.sections.create(section)
            if content_type is SectionContentType.QUIZ:
                await uow.quizzes.create_quiz(KnowledgeQuiz(course_id=course.id, section_id=section.id, slug=section.slug, title=title, description=description, status=status))
            await uow.commit()
            return result

    async def get_section(self, course_slug: str, module_slug: str, section_slug: str, include_archived: bool):
        course, module, _ = await self.get_module(course_slug, module_slug, include_archived)
        async with self.uow_factory() as uow:
            section = await uow.sections.get_by_slug(module.id, section_slug)
            await uow.rollback()
        if section is None or (not include_archived and section.status is ContentStatus.ARCHIVED):
            raise NotFoundError("section not found")
        return course, module, section

    async def update_section(self, course_slug: str, module_slug: str, section_slug: str, changes: dict[str, Any]) -> Section:
        async with self.uow_factory() as uow:
            course = await uow.courses.get_by_slug(course_slug)
            if course is None:
                raise NotFoundError("course not found")
            module = await uow.modules.get_by_slug(course.id, module_slug)
            if module is None:
                raise NotFoundError("module not found")
            section = await uow.sections.get_by_slug(module.id, section_slug)
            if section is None:
                raise NotFoundError("section not found")
            _apply_common_changes(section, changes)
            if "content_type" in changes and SectionContentType(changes["content_type"]) is not section.content_type:
                next_type = SectionContentType(changes["content_type"])
                if next_type is SectionContentType.QUIZ:
                    section.content_type = next_type
                    await uow.quizzes.create_quiz(KnowledgeQuiz(course_id=course.id, section_id=section.id, slug=section.slug, title=section.title, description=section.description, status=section.status))
                else:
                    await uow.quizzes.detach_section(section.id)
                    section.content_type = next_type
                if section.content_type is not SectionContentType.LAB_TASK:
                    section.terminal_enabled = False
                section.touch()
            if "position" in changes:
                raise ValidationError("position must be changed through the order endpoint")
            if "body" in changes:
                section.body = changes["body"]
                section.touch()
            if "requires_pass" in changes and changes["requires_pass"] is not None:
                section.requires_pass = changes["requires_pass"]
                section.touch()
            if "is_preview" in changes and changes["is_preview"] is not None:
                section.is_preview = changes["is_preview"]
                section.touch()
            if "terminal_enabled" in changes and changes["terminal_enabled"] is not None:
                terminal_enabled = bool(changes["terminal_enabled"])
                if terminal_enabled and section.content_type is not SectionContentType.LAB_TASK:
                    raise ValidationError("terminal_enabled is only valid for LAB_TASK sections")
                section.terminal_enabled = terminal_enabled
                section.touch()
            result = await uow.sections.update(section)
            await uow.commit()
            return result

    async def delete_section(self, course_slug: str, module_slug: str, section_slug: str) -> bool:
        course, module, section = await self.get_section(course_slug, module_slug, section_slug, include_archived=True)
        async with self.uow_factory() as uow:
            result = await uow.sections.delete(section.id)
            await uow.commit()
            return result

    async def reorder_modules(self, course_slug: str, ordered_ids: list[UUID]) -> None:
        async with self.uow_factory() as uow:
            course = await uow.courses.get_by_slug(course_slug)
            if course is None:
                raise NotFoundError("course not found")
            await uow.modules.reorder(course.id, ordered_ids)
            await uow.commit()

    async def reorder_sections(self, course_slug: str, module_slug: str, ordered_ids: list[UUID]) -> None:
        async with self.uow_factory() as uow:
            course = await uow.courses.get_by_slug(course_slug)
            if course is None:
                raise NotFoundError("course not found")
            module = await uow.modules.get_by_slug(course.id, module_slug)
            if module is None:
                raise NotFoundError("module not found")
            await uow.sections.reorder(module.id, ordered_ids)
            await uow.commit()


def _apply_common_changes(entity: Any, changes: dict[str, Any]) -> None:
    if "slug" in changes and changes["slug"] is not None and str(entity.slug) != str(Slug(changes["slug"])):
        raise ValidationError("content slugs are immutable")
    if "title" in changes or "description" in changes:
        title = changes.get("title", entity.title)
        description = changes["description"] if "description" in changes else entity.description
        entity.rename(title, description)
    if "status" in changes and changes["status"] is not None:
        target = ContentStatus(changes["status"])
        validate_status_transition(entity.status, target)
        entity.change_status(target)
