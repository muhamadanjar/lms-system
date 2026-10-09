from typing import Optional
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.entities.answer import Answer
from app.domain.entities.question import Question
from app.domain.entities.quiz import Quiz
from app.domain.exceptions import ConflictError, NotFoundError, ValidationError
from app.domain.value_objects.content import QuestionType, SectionContentType
from app.domain.value_objects.quiz_assessment import QuestionCode
from app.infrastructure.persistence.mappers.typed_content_mapper import to_answer, to_question, to_quiz
from app.infrastructure.persistence.models.answer import Answer as AnswerRow
from app.infrastructure.persistence.models.question import Question as QuestionRow
from app.infrastructure.persistence.models.question_code_sequence import QuestionCodeSequence
from app.infrastructure.persistence.models.quiz import Quiz as QuizRow
from app.infrastructure.persistence.models.section import Section
from app.infrastructure.persistence.models.module import Module as ModuleRow
from app.infrastructure.persistence.models.course import Course as CourseRow
from app.infrastructure.persistence.repositories.content_slug_repository import SqlModelContentSlugRegistry


class SqlModelQuizRepository:
    def __init__(self, session: AsyncSession, slugs: SqlModelContentSlugRegistry):
        self.session, self.slugs = session, slugs

    async def create_quiz(self, quiz: Quiz) -> Quiz:
        course_id = quiz.course_id
        if quiz.section_id is not None:
            section = await self.session.get(Section, quiz.section_id)
            if section is None:
                raise NotFoundError("section not found")
            if section.content_type != SectionContentType.QUIZ:
                raise ValidationError("quiz requires a QUIZ section")
            module = await self.session.get(ModuleRow, section.module_id)
            if module is None:
                raise NotFoundError("section module not found")
            if course_id is not None and course_id != module.course_id:
                raise ValidationError("quiz and section must belong to the same course")
            course_id = module.course_id
            if (await self.session.exec(select(QuizRow).where(QuizRow.section_id == quiz.section_id))).first():
                raise ConflictError("section already has a quiz")
        if course_id is None or await self.session.get(CourseRow, course_id) is None:
            raise NotFoundError("course not found")
        quiz.course_id = course_id
        self.session.add(QuizRow(id=quiz.id, slug=str(quiz.slug), status=quiz.status, created_at=quiz.created_at, updated_at=quiz.updated_at, course_id=course_id, section_id=quiz.section_id, title=quiz.title, description=quiz.description, is_exam=quiz.is_exam, max_attempts=quiz.max_attempts, passing_score=quiz.passing_score, answer_policy=quiz.answer_policy))
        await self.session.flush()
        return quiz

    async def list_by_course(self, course_id: UUID, offset: int = 0, limit: int = 100) -> list[Quiz]:
        rows = (await self.session.exec(select(QuizRow).where(QuizRow.course_id == course_id).order_by(QuizRow.created_at, QuizRow.id).offset(offset).limit(limit))).all()
        return [to_quiz(row) for row in rows]

    async def count_by_course(self, course_id: UUID) -> int:
        from sqlalchemy import func
        return int((await self.session.exec(select(func.count()).select_from(QuizRow).where(QuizRow.course_id == course_id))).one())

    async def get_section_reference(self, section_id: UUID):
        section = await self.session.get(Section, section_id)
        if section is None:
            return None
        module = await self.session.get(ModuleRow, section.module_id)
        if module is None:
            return None
        return {"module_slug": module.slug, "module_title": module.title, "section_slug": section.slug, "section_title": section.title}

    async def get_by_course_slug(self, course_id: UUID, slug: str) -> Optional[Quiz]:
        row = (await self.session.exec(select(QuizRow).where(QuizRow.course_id == course_id, QuizRow.slug == slug))).first()
        return to_quiz(row) if row else None

    async def link_to_section(self, course_id: UUID, quiz_slug: str, module_slug: str, section_slug: str) -> Quiz:
        quiz_row = (await self.session.exec(select(QuizRow).where(QuizRow.course_id == course_id, QuizRow.slug == quiz_slug).with_for_update())).first()
        if quiz_row is None:
            raise NotFoundError("quiz not found")
        module = (await self.session.exec(select(ModuleRow).where(ModuleRow.course_id == course_id, ModuleRow.slug == module_slug))).first()
        if module is None:
            raise NotFoundError("module not found")
        section = (await self.session.exec(select(Section).where(Section.module_id == module.id, Section.slug == section_slug).with_for_update())).first()
        if section is None:
            raise NotFoundError("section not found")
        if section.content_type != SectionContentType.QUIZ:
            raise ValidationError("quiz requires a QUIZ section")
        if quiz_row.section_id is not None:
            raise ConflictError("quiz is already linked to a section")
        if (await self.session.exec(select(QuizRow).where(QuizRow.section_id == section.id))).first():
            raise ConflictError("section already has a quiz")
        quiz_row.section_id = section.id
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise ConflictError("quiz or section is already linked") from exc
        return to_quiz(quiz_row)

    async def detach_section(self, section_id: UUID) -> None:
        rows = list((await self.session.exec(select(QuizRow).where(QuizRow.section_id == section_id))).all())
        for row in rows:
            row.section_id = None
        await self.session.flush()

    async def unlink_from_section(self, course_id: UUID, module_slug: str, section_slug: str) -> None:
        module = (await self.session.exec(select(ModuleRow).where(ModuleRow.course_id == course_id, ModuleRow.slug == module_slug))).first()
        if module is None:
            raise NotFoundError("module not found")
        section = (await self.session.exec(select(Section).where(Section.module_id == module.id, Section.slug == section_slug))).first()
        if section is None:
            raise NotFoundError("section not found")
        quiz_row = (await self.session.exec(select(QuizRow).where(QuizRow.section_id == section.id))).first()
        if quiz_row is None:
            raise NotFoundError("linked quiz not found")
        quiz_row.section_id = None
        await self.session.flush()

    async def delete_standalone(self, course_id: UUID, quiz_slug: str) -> bool:
        row = (await self.session.exec(select(QuizRow).where(QuizRow.course_id == course_id, QuizRow.slug == quiz_slug))).first()
        if row is None:
            raise NotFoundError("quiz not found")
        if row.section_id is not None:
            raise ConflictError("linked quiz must be unlinked before deletion")
        questions = list((await self.session.exec(select(QuestionRow).where(QuestionRow.quiz_id == row.id))).all())
        question_ids = [question.id for question in questions]
        answers = list((await self.session.exec(select(AnswerRow).where(AnswerRow.question_id.in_(question_ids)))).all()) if question_ids else []
        from app.infrastructure.persistence.models.quiz_sitting import QuizSitting as SittingRow
        sittings = list((await self.session.exec(select(SittingRow).where(SittingRow.quiz_id == row.id))).all())
        await self.session.delete(row)
        await self.session.flush()
        await self.slugs.release_ids([*question_ids, *[answer.id for answer in answers], *[sitting.id for sitting in sittings]])
        return True

    async def create_question(self, question: Question) -> Question:
        if await self.session.get(QuizRow, question.quiz_id) is None:
            raise NotFoundError("quiz not found")
        if question.question_code is None:
            question.question_code = await self.allocate_question_code()
        await self.slugs.reserve(str(question.slug), question.id, "question")
        self.session.add(QuestionRow(id=question.id, slug=str(question.slug), status=question.status, created_at=question.created_at, updated_at=question.updated_at, quiz_id=question.quiz_id, prompt=question.prompt, question_type=question.question_type, weight=question.weight, position=question.position, question_code=str(question.question_code)))
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise ConflictError(f"question_code is already reserved: {question.question_code}") from exc
        return question

    async def allocate_question_code(self) -> QuestionCode:
        """Allocate a deterministic code while respecting manual reservations."""
        sequence = await self.session.get(QuestionCodeSequence, "question_code")
        if sequence is None:
            sequence = QuestionCodeSequence(name="question_code", next_value=1)
            self.session.add(sequence)
            await self.session.flush()
        while True:
            code = QuestionCode(f"Q-{sequence.next_value:06d}")
            sequence.next_value += 1
            from app.infrastructure.persistence.models.base import utc_now
            sequence.updated_at = utc_now()
            if (await self.session.exec(select(QuestionRow).where(QuestionRow.question_code == str(code)))).first() is None:
                await self.session.flush()
                return code

    async def get_by_id(self, quiz_id: UUID) -> Optional[Quiz]:
        row = await self.session.get(QuizRow, quiz_id)
        return to_quiz(row) if row else None

    async def update_quiz(self, quiz: Quiz) -> Quiz:
        row = await self.session.get(QuizRow, quiz.id)
        if row is None:
            raise NotFoundError("quiz not found")
        row.slug, row.title, row.description, row.status = str(quiz.slug), quiz.title, quiz.description, quiz.status
        row.is_exam, row.max_attempts, row.passing_score, row.answer_policy, row.updated_at = quiz.is_exam, quiz.max_attempts, quiz.passing_score, quiz.answer_policy, quiz.updated_at
        await self.session.flush()
        return quiz

    async def update_question(self, question: Question) -> Question:
        row = await self.session.get(QuestionRow, question.id)
        if row is None:
            raise NotFoundError("question not found")
        if question.question_code is None:
            raise ValidationError("question_code is required")
        if row.question_code != str(question.question_code) and row.status == "PUBLISHED":
            raise ValidationError("published question_code is immutable")
        row.prompt, row.question_code, row.updated_at = question.prompt, str(question.question_code), question.updated_at
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise ConflictError(f"question_code is already reserved: {question.question_code}") from exc
        return question

    async def create_answer(self, answer: Answer) -> Answer:
        question = await self.session.get(QuestionRow, answer.question_id)
        if question is None:
            raise NotFoundError("question not found")
        question_type = QuestionType(question.question_type)
        if question_type is QuestionType.MULTICHOICE and answer.is_correct is None:
            raise ValidationError("MULTICHOICE answer requires is_correct")
        if question_type is QuestionType.DIRECT and answer.is_correct is not None:
            raise ValidationError("DIRECT answer cannot contain is_correct")
        await self.slugs.reserve(str(answer.slug), answer.id, "answer")
        self.session.add(AnswerRow(id=answer.id, slug=str(answer.slug), status=answer.status, created_at=answer.created_at, updated_at=answer.updated_at, question_id=answer.question_id, value=answer.value, position=answer.position, is_correct=answer.is_correct))
        await self.session.flush()
        return answer

    async def get_by_section(self, section_id: UUID) -> Optional[Quiz]:
        row = (await self.session.exec(select(QuizRow).where(QuizRow.section_id == section_id))).first()
        return to_quiz(row) if row else None

    async def get_question_by_slug(self, quiz_id: UUID, slug: str) -> Optional[Question]:
        row = (await self.session.exec(select(QuestionRow).where(QuestionRow.quiz_id == quiz_id, QuestionRow.slug == slug))).first()
        return to_question(row) if row else None

    async def list_questions(self, quiz_id: UUID) -> list[Question]:
        rows = (await self.session.exec(select(QuestionRow).where(QuestionRow.quiz_id == quiz_id).order_by(QuestionRow.position, QuestionRow.id))).all()
        return [to_question(row) for row in rows]

    async def list_answers(self, question: Question) -> list[Answer]:
        rows = (await self.session.exec(select(AnswerRow).where(AnswerRow.question_id == question.id).order_by(AnswerRow.position, AnswerRow.id))).all()
        return [to_answer(row, question.question_type) for row in rows]

    async def save_question_with_answers(self, question: Question, answers: list[Answer]) -> tuple[Question, list[Answer]]:
        existing = await self.get_question_by_slug(question.quiz_id, str(question.slug))
        if existing is None:
            await self.create_question(question)
        else:
            question.id = existing.id
            question.created_at = existing.created_at
            question.question_code = existing.question_code
            await self.update_question(question)
        old_rows = list((await self.session.exec(select(AnswerRow).where(AnswerRow.question_id == question.id))).all())
        old_ids = [row.id for row in old_rows]
        if old_ids:
            for row in old_rows:
                await self.session.delete(row)
            await self.session.flush()
            await self.slugs.release_ids(old_ids)
        persisted: list[Answer] = []
        for answer in answers:
            answer.question_id = question.id
            await self.create_answer(answer)
            persisted.append(answer)
        return question, persisted

    async def delete_question(self, quiz_id: UUID, question_slug: str) -> None:
        row = (await self.session.exec(select(QuestionRow).where(QuestionRow.quiz_id == quiz_id, QuestionRow.slug == question_slug))).first()
        if row is None:
            raise NotFoundError("question not found")
        answers = list((await self.session.exec(select(AnswerRow).where(AnswerRow.question_id == row.id))).all())
        ids = [row.id, *(answer.id for answer in answers)]
        for answer in answers:
            await self.session.delete(answer)
        await self.session.flush()
        await self.session.delete(row)
        await self.session.flush()
        await self.slugs.release_ids(ids)

    async def reorder_questions(self, quiz_id: UUID, ordered_slugs: list[str]) -> None:
        rows = list((await self.session.exec(select(QuestionRow).where(QuestionRow.quiz_id == quiz_id).order_by(QuestionRow.position, QuestionRow.id).with_for_update())).all())
        by_slug = {row.slug: row for row in rows}
        if len(ordered_slugs) != len(by_slug) or len(set(ordered_slugs)) != len(ordered_slugs) or set(ordered_slugs) != set(by_slug):
            raise ValidationError("order must include every question exactly once")
        temporary_start = max((row.position for row in rows), default=-1) + len(rows) + 1
        for index, slug in enumerate(ordered_slugs):
            by_slug[slug].position = temporary_start + index
        await self.session.flush()
        for index, slug in enumerate(ordered_slugs):
            by_slug[slug].position = index
        await self.session.flush()
