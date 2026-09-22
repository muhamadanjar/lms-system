from typing import Optional
from uuid import UUID

from sqlalchemy import delete
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.entities.course import Course
from app.domain.entities.module import Module
from app.domain.entities.section import CourseHierarchy, Section
from app.domain.exceptions import NotFoundError, ValidationError
from app.infrastructure.persistence.mappers.content_mapper import to_course, to_module, to_section
from app.infrastructure.persistence.models.answer import Answer
from app.infrastructure.persistence.models.content_slug_registry import ContentSlugRegistry
from app.infrastructure.persistence.models.course import Course as CourseRow
from app.infrastructure.persistence.models.lab_environment_settings import LabEnvironmentSettings
from app.infrastructure.persistence.models.module import Module as ModuleRow
from app.infrastructure.persistence.models.question import Question
from app.infrastructure.persistence.models.quiz import Quiz
from app.infrastructure.persistence.models.quiz_sitting import QuizSitting
from app.infrastructure.persistence.models.section import Section as SectionRow
from app.infrastructure.persistence.repositories.content_slug_repository import SqlModelContentSlugRegistry


class SqlModelCourseRepository:
    def __init__(self, session: AsyncSession, slugs: SqlModelContentSlugRegistry):
        self.session = session
        self.slugs = slugs

    async def create(self, course: Course) -> Course:
        await self.slugs.reserve(str(course.slug), course.id, "course")
        self.session.add(CourseRow(
            id=course.id, slug=str(course.slug), status=course.status, created_at=course.created_at,
            updated_at=course.updated_at, title=course.title, description=course.description,
        ))
        await self.session.flush()
        return course

    async def get_by_id(self, course_id: UUID) -> Optional[Course]:
        row = await self.session.get(CourseRow, course_id)
        return to_course(row) if row else None

    async def get_by_slug(self, slug: str) -> Optional[Course]:
        row = (await self.session.exec(select(CourseRow).where(CourseRow.slug == slug))).first()
        return to_course(row) if row else None

    async def list(self, status: str | None = None, include_archived: bool = False, offset: int = 0, limit: int = 20) -> list[Course]:
        query = select(CourseRow).order_by(CourseRow.created_at.desc(), CourseRow.id).offset(offset).limit(limit)
        if status is not None:
            query = query.where(CourseRow.status == status)
        elif not include_archived:
            query = query.where(CourseRow.status != "ARCHIVED")
        return [to_course(row) for row in (await self.session.exec(query)).all()]

    async def count(self, status: str | None = None, include_archived: bool = False) -> int:
        from sqlalchemy import func
        query = select(func.count()).select_from(CourseRow)
        if status is not None:
            query = query.where(CourseRow.status == status)
        elif not include_archived:
            query = query.where(CourseRow.status != "ARCHIVED")
        return int((await self.session.exec(query)).one())

    async def get_hierarchy(self, course_id: UUID, include_archived: bool = False) -> Optional[CourseHierarchy]:
        course_row = await self.session.get(CourseRow, course_id)
        if course_row is None:
            return None
        course = to_course(course_row)
        module_query = select(ModuleRow).where(ModuleRow.course_id == course_id).order_by(ModuleRow.position, ModuleRow.id)
        if not include_archived:
            module_query = module_query.where(ModuleRow.status != "ARCHIVED")
        module_rows = list((await self.session.exec(module_query)).all())
        modules = [to_module(row) for row in module_rows]
        sections_by_module: dict[UUID, list[Section]] = {}
        for module in modules:
            section_query = select(SectionRow).where(SectionRow.module_id == module.id).order_by(SectionRow.position, SectionRow.id)
            if not include_archived:
                section_query = section_query.where(SectionRow.status != "ARCHIVED")
            sections_by_module[module.id] = [to_section(row) for row in (await self.session.exec(section_query)).all()]
        return CourseHierarchy(course=course, modules=modules, sections_by_module=sections_by_module)

    async def update(self, course: Course) -> Course:
        row = await self.session.get(CourseRow, course.id)
        if row is None:
            raise NotFoundError("course not found")
        if row.slug != str(course.slug):
            raise ValidationError("content slugs are immutable")
        row.title, row.description, row.status, row.updated_at = course.title, course.description, course.status, course.updated_at
        await self.session.flush()
        return course

    async def delete(self, course_id: UUID) -> bool:
        module_rows = list((await self.session.exec(select(ModuleRow).where(ModuleRow.course_id == course_id))).all())
        module_ids = [row.id for row in module_rows]
        section_rows = list((await self.session.exec(select(SectionRow).where(SectionRow.module_id.in_(module_ids)))).all()) if module_ids else []
        section_ids = [row.id for row in section_rows]
        quiz_rows = list((await self.session.exec(select(Quiz).where(Quiz.section_id.in_(section_ids)))).all()) if section_ids else []
        quiz_ids = [row.id for row in quiz_rows]
        question_rows = list((await self.session.exec(select(Question).where(Question.quiz_id.in_(quiz_ids)))).all()) if quiz_ids else []
        question_ids = [row.id for row in question_rows]
        answer_rows = list((await self.session.exec(select(Answer).where(Answer.question_id.in_(question_ids)))).all()) if question_ids else []
        lab_rows = list((await self.session.exec(select(LabEnvironmentSettings).where(LabEnvironmentSettings.section_id.in_(section_ids)))).all()) if section_ids else []
        sitting_rows = list((await self.session.exec(select(QuizSitting).where(QuizSitting.quiz_id.in_(quiz_ids)))).all()) if quiz_ids else []
        await self.session.execute(delete(Answer).where(Answer.question_id.in_(question_ids))) if question_ids else None
        await self.session.execute(delete(Question).where(Question.id.in_(question_ids))) if question_ids else None
        await self.session.execute(delete(QuizSitting).where(QuizSitting.quiz_id.in_(quiz_ids))) if quiz_ids else None
        await self.session.execute(delete(Quiz).where(Quiz.id.in_(quiz_ids))) if quiz_ids else None
        await self.session.execute(delete(LabEnvironmentSettings).where(LabEnvironmentSettings.section_id.in_(section_ids))) if section_ids else None
        await self.session.execute(delete(SectionRow).where(SectionRow.id.in_(section_ids))) if section_ids else None
        await self.session.execute(delete(ModuleRow).where(ModuleRow.id.in_(module_ids))) if module_ids else None
        await self.slugs.release_ids(
            [course_id, *module_ids, *section_ids, *quiz_ids, *question_ids,
             *[row.id for row in answer_rows], *[row.id for row in lab_rows], *[row.id for row in sitting_rows]]
        )
        result = await self.session.execute(delete(CourseRow).where(CourseRow.id == course_id))
        await self.session.flush()
        return bool(result.rowcount)
