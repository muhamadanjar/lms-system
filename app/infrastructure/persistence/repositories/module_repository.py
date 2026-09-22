from typing import Optional
from uuid import UUID

from sqlalchemy import delete
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.entities.module import Module
from app.domain.exceptions import NotFoundError, ValidationError
from app.infrastructure.persistence.mappers.content_mapper import to_module
from app.infrastructure.persistence.models.module import Module as ModuleRow
from app.infrastructure.persistence.models.answer import Answer
from app.infrastructure.persistence.models.lab_environment_settings import LabEnvironmentSettings
from app.infrastructure.persistence.models.question import Question
from app.infrastructure.persistence.models.quiz import Quiz
from app.infrastructure.persistence.models.quiz_sitting import QuizSitting
from app.infrastructure.persistence.models.section import Section as SectionRow
from app.infrastructure.persistence.repositories.content_slug_repository import SqlModelContentSlugRegistry


class SqlModelModuleRepository:
    def __init__(self, session: AsyncSession, slugs: SqlModelContentSlugRegistry):
        self.session, self.slugs = session, slugs

    async def create(self, module: Module) -> Module:
        from app.infrastructure.persistence.models.course import Course
        if await self.session.get(Course, module.course_id) is None:
            raise NotFoundError("course not found")
        await self.slugs.reserve(str(module.slug), module.id, "module")
        self.session.add(ModuleRow(id=module.id, slug=str(module.slug), status=module.status, created_at=module.created_at, updated_at=module.updated_at, course_id=module.course_id, title=module.title, description=module.description, position=module.position))
        await self.session.flush()
        return module

    async def get_by_id(self, module_id: UUID) -> Optional[Module]:
        row = await self.session.get(ModuleRow, module_id)
        return to_module(row) if row else None

    async def get_by_slug(self, course_id: UUID, slug: str) -> Optional[Module]:
        row = (await self.session.exec(select(ModuleRow).where(ModuleRow.course_id == course_id, ModuleRow.slug == slug))).first()
        return to_module(row) if row else None

    async def list_by_course(self, course_id: UUID, include_archived: bool = False, offset: int = 0, limit: int = 20) -> list[Module]:
        query = select(ModuleRow).where(ModuleRow.course_id == course_id).order_by(ModuleRow.position, ModuleRow.id).offset(offset).limit(limit)
        if not include_archived:
            query = query.where(ModuleRow.status != "ARCHIVED")
        return [to_module(row) for row in (await self.session.exec(query)).all()]

    async def count_by_course(self, course_id: UUID, include_archived: bool = False) -> int:
        from sqlalchemy import func
        query = select(func.count()).select_from(ModuleRow).where(ModuleRow.course_id == course_id)
        if not include_archived:
            query = query.where(ModuleRow.status != "ARCHIVED")
        return int((await self.session.exec(query)).one())

    async def update(self, module: Module) -> Module:
        row = await self.session.get(ModuleRow, module.id)
        if row is None:
            raise NotFoundError("module not found")
        if row.slug != str(module.slug) or row.course_id != module.course_id:
            raise ValidationError("module slug and parent are immutable in this operation")
        row.title, row.description, row.position, row.status, row.updated_at = module.title, module.description, module.position, module.status, module.updated_at
        await self.session.flush()
        return module

    async def reorder(self, course_id: UUID, ordered_ids: list[UUID]) -> None:
        rows = list((await self.session.exec(select(ModuleRow).where(ModuleRow.course_id == course_id))).all())
        if {row.id for row in rows} != set(ordered_ids):
            raise ValidationError("reorder must contain exactly the existing modules")
        by_id = {row.id: row for row in rows}
        for offset, row in enumerate(rows, start=1):
            row.position = -offset
        await self.session.flush()
        for position, module_id in enumerate(ordered_ids):
            by_id[module_id].position = position
        await self.session.flush()

    async def delete(self, module_id: UUID) -> bool:
        row = await self.session.get(ModuleRow, module_id)
        if row is None:
            return False
        sections = list((await self.session.exec(select(SectionRow).where(SectionRow.module_id == module_id))).all())
        section_ids = [section.id for section in sections]
        labs = list((await self.session.exec(select(LabEnvironmentSettings).where(LabEnvironmentSettings.section_id.in_(section_ids)))).all()) if section_ids else []
        quizzes = list((await self.session.exec(select(Quiz).where(Quiz.section_id.in_(section_ids)))).all()) if section_ids else []
        quiz_ids = [quiz.id for quiz in quizzes]
        questions = list((await self.session.exec(select(Question).where(Question.quiz_id.in_(quiz_ids)))).all()) if quiz_ids else []
        question_ids = [question.id for question in questions]
        answers = list((await self.session.exec(select(Answer).where(Answer.question_id.in_(question_ids)))).all()) if question_ids else []
        sittings = list((await self.session.exec(select(QuizSitting).where(QuizSitting.quiz_id.in_(quiz_ids)))).all()) if quiz_ids else []
        if question_ids:
            await self.session.execute(delete(Answer).where(Answer.question_id.in_(question_ids)))
            await self.session.execute(delete(Question).where(Question.id.in_(question_ids)))
        if quiz_ids:
            await self.session.execute(delete(QuizSitting).where(QuizSitting.quiz_id.in_(quiz_ids)))
            await self.session.execute(delete(Quiz).where(Quiz.id.in_(quiz_ids)))
        if section_ids:
            await self.session.execute(delete(LabEnvironmentSettings).where(LabEnvironmentSettings.section_id.in_(section_ids)))
        await self.session.execute(delete(SectionRow).where(SectionRow.module_id == module_id))
        await self.slugs.release_ids([module_id, *section_ids, *quiz_ids, *question_ids, *[x.id for x in answers], *[x.id for x in labs], *[x.id for x in sittings]])
        await self.session.delete(row)
        await self.session.flush()
        return True
