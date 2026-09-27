from datetime import datetime, timezone
from collections import defaultdict
from typing import Optional
from uuid import UUID

from sqlalchemy import delete
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.entities.quiz_sitting import QuizSitting
from app.domain.entities.quiz_sitting_snapshot import (
    QuizSittingOptionSnapshot,
    QuizSittingQuestionResult,
    QuizSittingQuestionSnapshot,
    QuizSittingResult,
)
from app.domain.exceptions import ConflictError, NotFoundError, ValidationError
from app.domain.value_objects.content import QuestionType, QuizAttemptState
from app.domain.value_objects.quiz_assessment import AnswerPolicy, QuestionCode, QuestionResultOutcome
from app.infrastructure.persistence.mappers.typed_content_mapper import to_sitting
from app.infrastructure.persistence.models.quiz import Quiz
from app.infrastructure.persistence.models.quiz_sitting import QuizSitting as SittingRow
from app.infrastructure.persistence.models.quiz_exam_attempt_counter import QuizExamAttemptCounter
from app.infrastructure.persistence.models.quiz_sitting_answer_selection import QuizSittingAnswerSelection
from app.infrastructure.persistence.models.quiz_sitting_option import QuizSittingOption
from app.infrastructure.persistence.models.quiz_sitting_question import QuizSittingQuestion
from app.infrastructure.persistence.models.quiz_sitting_question_result import QuizSittingQuestionResult as ResultRow
from app.infrastructure.persistence.repositories.content_slug_repository import SqlModelContentSlugRegistry


class SqlModelQuizSittingRepository:
    def __init__(self, session: AsyncSession, slugs: SqlModelContentSlugRegistry):
        self.session, self.slugs = session, slugs

    async def create(self, sitting: QuizSitting) -> QuizSitting:
        if await self.session.get(Quiz, sitting.quiz_id) is None:
            raise NotFoundError("quiz not found")
        active = (await self.session.exec(select(SittingRow).where(SittingRow.quiz_id == sitting.quiz_id, SittingRow.learner_id == sitting.learner_id, SittingRow.attempt_state == QuizAttemptState.IN_PROGRESS))).first()
        if active:
            raise ConflictError("learner already has an active sitting for this quiz")
        await self.slugs.reserve(str(sitting.slug), sitting.id, "quiz_sitting")
        self.session.add(SittingRow(id=sitting.id, slug=str(sitting.slug), status=sitting.status, created_at=sitting.created_at, updated_at=sitting.updated_at, quiz_id=sitting.quiz_id, learner_id=sitting.learner_id, attempt_state=sitting.attempt_state, started_at=sitting.started_at, submitted_at=sitting.submitted_at, active_sitting_key=self._active_key(sitting.quiz_id, sitting.learner_id), total_score=sitting.total_score))
        await self.session.flush()
        return sitting

    async def get_by_id(self, sitting_id: UUID) -> Optional[QuizSitting]:
        row = await self.session.get(SittingRow, sitting_id)
        return to_sitting(row) if row else None

    async def update(self, sitting: QuizSitting) -> QuizSitting:
        row = await self.session.get(SittingRow, sitting.id)
        if row is None:
            raise NotFoundError("quiz sitting not found")
        row.attempt_state, row.submitted_at, row.status, row.updated_at, row.total_score = sitting.attempt_state, sitting.submitted_at, sitting.status, sitting.updated_at, sitting.total_score
        row.active_sitting_key = self._active_key(sitting.quiz_id, sitting.learner_id) if sitting.attempt_state is QuizAttemptState.IN_PROGRESS else None
        await self.session.flush()
        return sitting

    @staticmethod
    def _active_key(quiz_id: UUID, learner_id: str) -> str:
        return f"{quiz_id}:{learner_id}"

    async def get_active(self, quiz_id: UUID, learner_id: str) -> Optional[QuizSitting]:
        row = (await self.session.exec(select(SittingRow).where(SittingRow.active_sitting_key == self._active_key(quiz_id, learner_id)))).first()
        return to_sitting(row) if row else None

    async def save_snapshot(self, snapshots: list[QuizSittingQuestionSnapshot]) -> None:
        for snapshot in snapshots:
            self.session.add(QuizSittingQuestion(
                id=snapshot.id, sitting_id=snapshot.sitting_id, source_question_id=snapshot.source_question_id,
                question_code=str(snapshot.question_code), prompt=snapshot.prompt,
                question_type=str(snapshot.question_type), answer_policy=str(snapshot.answer_policy), position=snapshot.position,
            ))
            for option in snapshot.options:
                self.session.add(QuizSittingOption(
                    id=option.id, sitting_question_id=snapshot.id, source_answer_id=option.source_answer_id,
                    value=option.value, position=option.position, is_correct=option.is_correct,
                ))
        await self.session.flush()

    async def get_snapshot(self, sitting_id: UUID) -> list[QuizSittingQuestionSnapshot]:
        questions = list((await self.session.exec(select(QuizSittingQuestion).where(QuizSittingQuestion.sitting_id == sitting_id).order_by(QuizSittingQuestion.position, QuizSittingQuestion.id))).all())
        if not questions:
            return []
        question_ids = [question.id for question in questions]
        options = list((await self.session.exec(select(QuizSittingOption).where(QuizSittingOption.sitting_question_id.in_(question_ids)).order_by(QuizSittingOption.position, QuizSittingOption.id))).all())
        by_question: dict[UUID, list[QuizSittingOptionSnapshot]] = defaultdict(list)
        for option in options:
            by_question[option.sitting_question_id].append(QuizSittingOptionSnapshot(id=option.id, source_answer_id=option.source_answer_id, value=option.value, position=option.position, is_correct=option.is_correct))
        return [QuizSittingQuestionSnapshot(id=row.id, sitting_id=row.sitting_id, source_question_id=row.source_question_id, question_code=QuestionCode(row.question_code), prompt=row.prompt, question_type=QuestionType(row.question_type), answer_policy=AnswerPolicy(row.answer_policy), position=row.position, options=tuple(by_question[row.id])) for row in questions]

    async def replace_selection(self, sitting_question_id: UUID, option_ids: set[UUID]) -> None:
        await self.session.execute(delete(QuizSittingAnswerSelection).where(QuizSittingAnswerSelection.sitting_question_id == sitting_question_id))
        for option_id in option_ids:
            self.session.add(QuizSittingAnswerSelection(sitting_question_id=sitting_question_id, sitting_option_id=option_id))
        await self.session.flush()

    async def selected_option_ids(self, sitting_id: UUID) -> dict[UUID, set[UUID]]:
        statement = select(QuizSittingAnswerSelection).join(QuizSittingQuestion, QuizSittingAnswerSelection.sitting_question_id == QuizSittingQuestion.id).where(QuizSittingQuestion.sitting_id == sitting_id)
        rows = list((await self.session.exec(statement)).all())
        selected: dict[UUID, set[UUID]] = defaultdict(set)
        for row in rows:
            selected[row.sitting_question_id].add(row.sitting_option_id)
        return selected

    async def save_final_result(self, sitting: QuizSitting, result: QuizSittingResult) -> None:
        existing = await self.get_final_result(sitting.id)
        if existing is not None:
            return
        for item in result.question_results:
            self.session.add(ResultRow(sitting_question_id=item.sitting_question_id, question_code=str(item.question_code), outcome=str(item.outcome), score=item.score, finalized_at=item.finalized_at))
        await self.update(sitting)

    async def get_final_result(self, sitting_id: UUID) -> QuizSittingResult | None:
        sitting = await self.get_by_id(sitting_id)
        if sitting is None or sitting.attempt_state is not QuizAttemptState.GRADED:
            return None
        snapshot = await self.get_snapshot(sitting_id)
        rows = list((await self.session.exec(select(ResultRow).join(QuizSittingQuestion, ResultRow.sitting_question_id == QuizSittingQuestion.id).where(QuizSittingQuestion.sitting_id == sitting_id).order_by(QuizSittingQuestion.position))).all())
        if len(rows) != len(snapshot):
            raise ValidationError("graded sitting has incomplete question results")
        results = tuple(QuizSittingQuestionResult(sitting_question_id=row.sitting_question_id, question_code=QuestionCode(row.question_code), outcome=QuestionResultOutcome(row.outcome), score=row.score, finalized_at=row.finalized_at) for row in rows)
        return QuizSittingResult(sitting_id=sitting.id, quiz_id=sitting.quiz_id, available_question_codes=tuple(question.question_code for question in snapshot), question_results=results, total_score=sitting.total_score or 0, finalized_at=results[0].finalized_at)

    async def list_final_results(self, quiz_id: UUID, learner_id: str) -> list[QuizSittingResult]:
        rows = list((await self.session.exec(select(SittingRow).where(SittingRow.quiz_id == quiz_id, SittingRow.learner_id == learner_id, SittingRow.attempt_state == QuizAttemptState.GRADED).order_by(SittingRow.updated_at, SittingRow.id))).all())
        results = [await self.get_final_result(row.id) for row in rows]
        return [result for result in results if result is not None]

    async def reserve_exam_finalization(self, quiz_id: UUID, learner_id: str, max_attempts: int) -> None:
        counter = (await self.session.exec(
            select(QuizExamAttemptCounter)
            .where(QuizExamAttemptCounter.quiz_id == quiz_id, QuizExamAttemptCounter.learner_id == learner_id)
            .with_for_update()
        )).first()
        if counter is None:
            counter = QuizExamAttemptCounter(quiz_id=quiz_id, learner_id=learner_id, finalized_attempts=0)
            self.session.add(counter)
            await self.session.flush()
        if counter.finalized_attempts >= max_attempts:
            raise ConflictError("EXAM_ATTEMPT_LIMIT_REACHED")
        counter.finalized_attempts += 1
        from app.infrastructure.persistence.models.base import utc_now
        counter.updated_at = utc_now()
        await self.session.flush()
