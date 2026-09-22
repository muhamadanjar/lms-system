from typing import Optional
from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.entities.answer import Answer
from app.domain.entities.question import Question
from app.domain.entities.quiz import Quiz
from app.domain.exceptions import ConflictError, NotFoundError, ValidationError
from app.domain.value_objects.content import QuestionType, SectionContentType
from app.infrastructure.persistence.mappers.typed_content_mapper import to_answer, to_question, to_quiz
from app.infrastructure.persistence.models.answer import Answer as AnswerRow
from app.infrastructure.persistence.models.question import Question as QuestionRow
from app.infrastructure.persistence.models.quiz import Quiz as QuizRow
from app.infrastructure.persistence.models.section import Section
from app.infrastructure.persistence.repositories.content_slug_repository import SqlModelContentSlugRegistry


class SqlModelQuizRepository:
    def __init__(self, session: AsyncSession, slugs: SqlModelContentSlugRegistry):
        self.session, self.slugs = session, slugs

    async def create_quiz(self, quiz: Quiz) -> Quiz:
        section = await self.session.get(Section, quiz.section_id)
        if section is None:
            raise NotFoundError("section not found")
        if section.content_type != SectionContentType.QUIZ:
            raise ValidationError("quiz requires a QUIZ section")
        if (await self.session.exec(select(QuizRow).where(QuizRow.section_id == quiz.section_id))).first():
            raise ConflictError("section already has a quiz")
        await self.slugs.reserve(str(quiz.slug), quiz.id, "quiz")
        self.session.add(QuizRow(id=quiz.id, slug=str(quiz.slug), status=quiz.status, created_at=quiz.created_at, updated_at=quiz.updated_at, section_id=quiz.section_id))
        await self.session.flush()
        return quiz

    async def create_question(self, question: Question) -> Question:
        if await self.session.get(QuizRow, question.quiz_id) is None:
            raise NotFoundError("quiz not found")
        await self.slugs.reserve(str(question.slug), question.id, "question")
        self.session.add(QuestionRow(id=question.id, slug=str(question.slug), status=question.status, created_at=question.created_at, updated_at=question.updated_at, quiz_id=question.quiz_id, prompt=question.prompt, question_type=question.question_type, weight=question.weight, position=question.position))
        await self.session.flush()
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

    async def list_questions(self, quiz_id: UUID) -> list[Question]:
        rows = (await self.session.exec(select(QuestionRow).where(QuestionRow.quiz_id == quiz_id).order_by(QuestionRow.position, QuestionRow.id))).all()
        return [to_question(row) for row in rows]

    async def list_answers(self, question: Question) -> list[Answer]:
        rows = (await self.session.exec(select(AnswerRow).where(AnswerRow.question_id == question.id).order_by(AnswerRow.position, AnswerRow.id))).all()
        return [to_answer(row, question.question_type) for row in rows]
