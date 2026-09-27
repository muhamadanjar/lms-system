"""Transactional learner quiz-sitting workflow."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.application.dto.quiz_sittings import (
    AnswerSelectionInput,
    QuestionScoreDTO,
    QuizResultSummaryDTO,
    QuizSittingDraftDTO,
    QuizSittingResultDTO,
)
from app.domain.entities.quiz_sitting import QuizSitting
from app.domain.entities.quiz_sitting_snapshot import (
    QuizSittingOptionSnapshot,
    QuizSittingQuestionSnapshot,
    QuizSittingResult,
)
from app.domain.exceptions import NotFoundError, ValidationError
from app.domain.services.quiz_evaluation import evaluate_snapshot_question
from app.domain.value_objects.content import QuestionType, QuizAttemptState
from app.domain.value_objects.quiz_assessment import QuestionCode


class QuizSittingUseCases:
    """Coordinate ownership, snapshotting, selection validation, and final scoring."""

    def __init__(self, uow):
        self.uow = uow

    async def start_or_resume(self, quiz_id: UUID, learner_id: str) -> tuple[QuizSittingDraftDTO, bool]:
        async with self.uow as uow:
            quiz = await uow.quizzes.get_by_id(quiz_id)
            if quiz is None:
                raise NotFoundError("quiz not found")
            active = await uow.sittings.get_active(quiz_id, learner_id)
            if active is not None:
                return await self._draft_dto(uow, active), False
            questions = await uow.quizzes.list_questions(quiz_id)
            if any(question.question_type is not QuestionType.MULTICHOICE for question in questions):
                raise ValidationError("DIRECT questions are not supported for quiz sittings")
            sitting = QuizSitting(quiz_id=quiz_id, learner_id=learner_id, slug=f"quiz-sitting-{uuid4().hex[:20]}")
            await uow.sittings.create(sitting)
            snapshots: list[QuizSittingQuestionSnapshot] = []
            for question in questions:
                if question.question_code is None:
                    raise ValidationError("question_code is required before starting a sitting")
                answers = await uow.quizzes.list_answers(question)
                snapshots.append(QuizSittingQuestionSnapshot(
                    sitting_id=sitting.id,
                    source_question_id=question.id,
                    question_code=question.question_code,
                    prompt=question.prompt,
                    question_type=question.question_type,
                    answer_policy=quiz.answer_policy,
                    position=question.position,
                    options=tuple(QuizSittingOptionSnapshot(source_answer_id=answer.id, value=answer.value, position=answer.position, is_correct=bool(answer.is_correct)) for answer in answers),
                ))
            if not snapshots:
                raise ValidationError("quiz must contain at least one question")
            await uow.sittings.save_snapshot(snapshots)
            await uow.commit()
            return self._draft_from_snapshot(sitting, snapshots), True

    async def start_or_resume_for_path(self, course_slug: str, module_slug: str, section_slug: str, learner_id: str) -> tuple[QuizSittingDraftDTO, bool]:
        async with self.uow as uow:
            course = await uow.courses.get_by_slug(course_slug)
            if course is None:
                raise NotFoundError("course not found")
            module = await uow.modules.get_by_slug(course.id, module_slug)
            if module is None:
                raise NotFoundError("module not found")
            section = await uow.sections.get_by_slug(module.id, section_slug)
            if section is None:
                raise NotFoundError("quiz section not found")
            quiz = await uow.quizzes.get_by_section(section.id)
            if quiz is None:
                raise NotFoundError("quiz not found")
            # Do not use start_or_resume here: both methods own a UoW boundary.
            active = await uow.sittings.get_active(quiz.id, learner_id)
            if active is not None:
                return await self._draft_dto(uow, active), False
            questions = await uow.quizzes.list_questions(quiz.id)
            if not questions or any(question.question_type is not QuestionType.MULTICHOICE for question in questions):
                raise ValidationError("quiz sittings require at least one MULTICHOICE-only question")
            sitting = QuizSitting(quiz_id=quiz.id, learner_id=learner_id, slug=f"quiz-sitting-{uuid4().hex[:20]}")
            await uow.sittings.create(sitting)
            snapshots = []
            for question in questions:
                if question.question_code is None:
                    raise ValidationError("question_code is required before starting a sitting")
                answers = await uow.quizzes.list_answers(question)
                snapshots.append(QuizSittingQuestionSnapshot(sitting_id=sitting.id, source_question_id=question.id, question_code=question.question_code, prompt=question.prompt, question_type=question.question_type, answer_policy=quiz.answer_policy, position=question.position, options=tuple(QuizSittingOptionSnapshot(source_answer_id=answer.id, value=answer.value, position=answer.position, is_correct=bool(answer.is_correct)) for answer in answers)))
            await uow.sittings.save_snapshot(snapshots)
            await uow.commit()
            return self._draft_from_snapshot(sitting, snapshots), True

    async def save_selections(self, sitting_id: UUID, learner_id: str, answers: tuple[AnswerSelectionInput, ...]) -> QuizSittingDraftDTO:
        async with self.uow as uow:
            sitting = await self._owned_sitting(uow, sitting_id, learner_id)
            self._require_draft(sitting)
            snapshot = await uow.sittings.get_snapshot(sitting_id)
            by_code = {str(question.question_code): question for question in snapshot}
            seen_codes: set[str] = set()
            for answer in answers:
                code = str(QuestionCode(answer.question_code))
                if code in seen_codes:
                    raise ValidationError("duplicate question_code in answer selections")
                seen_codes.add(code)
                question = by_code.get(code)
                if question is None:
                    raise ValidationError("question_code is not available in this sitting")
                option_ids = set(answer.option_ids)
                if len(option_ids) != len(answer.option_ids):
                    raise ValidationError("duplicate option_id in answer selection")
                if question.answer_policy.value == "SINGLE" and len(option_ids) > 1:
                    raise ValidationError("single-answer question accepts at most one option")
                allowed_option_ids = {option.id for option in question.options}
                if not option_ids.issubset(allowed_option_ids):
                    raise ValidationError("option_id does not belong to question snapshot")
                await uow.sittings.replace_selection(question.id, option_ids)
            await uow.commit()
            return self._draft_from_snapshot(sitting, snapshot)

    async def finalize(self, sitting_id: UUID, learner_id: str) -> QuizSittingResultDTO:
        async with self.uow as uow:
            sitting = await self._owned_sitting(uow, sitting_id, learner_id)
            existing = await uow.sittings.get_final_result(sitting_id)
            if existing is not None:
                return self._result_dto(existing)
            self._require_draft(sitting)
            quiz = await uow.quizzes.get_by_id(sitting.quiz_id)
            if quiz is None:
                raise NotFoundError("quiz not found")
            snapshot = await uow.sittings.get_snapshot(sitting_id)
            selected = await uow.sittings.selected_option_ids(sitting_id)
            finalized_at = datetime.now(timezone.utc)
            question_results = tuple(evaluate_snapshot_question(question, selected.get(question.id, set()), finalized_at) for question in snapshot)
            result = QuizSittingResult(
                sitting_id=sitting.id,
                quiz_id=sitting.quiz_id,
                available_question_codes=tuple(question.question_code for question in snapshot),
                question_results=question_results,
                total_score=sum(item.score for item in question_results),
                finalized_at=finalized_at,
            )
            if quiz.is_exam:
                await uow.sittings.reserve_exam_finalization(quiz.id, learner_id, quiz.max_attempts)
            sitting.finalize(result.total_score)
            await uow.sittings.save_final_result(sitting, result)
            await uow.commit()
            return self._result_dto(result)

    async def get(self, sitting_id: UUID, learner_id: str) -> QuizSittingDraftDTO | QuizSittingResultDTO:
        async with self.uow as uow:
            sitting = await self._owned_sitting(uow, sitting_id, learner_id)
            result = await uow.sittings.get_final_result(sitting_id)
            return self._result_dto(result) if result is not None else await self._draft_dto(uow, sitting)

    async def summary(self, quiz_id: UUID, learner_id: str) -> QuizResultSummaryDTO:
        async with self.uow as uow:
            quiz = await uow.quizzes.get_by_id(quiz_id)
            if quiz is None:
                raise NotFoundError("quiz not found")
            results = await uow.sittings.list_final_results(quiz_id, learner_id)
            canonical = max(results, key=lambda result: result.total_score, default=None)
            return QuizResultSummaryDTO(
                quiz_id=quiz_id,
                is_exam=quiz.is_exam,
                best_score=canonical.total_score if canonical else None,
                finalized_attempts=len(results),
                max_attempts=quiz.max_attempts if quiz.is_exam else None,
                result=self._result_dto(canonical) if canonical else None,
            )

    async def summary_for_path(self, course_slug: str, module_slug: str, section_slug: str, learner_id: str) -> QuizResultSummaryDTO:
        async with self.uow as uow:
            course = await uow.courses.get_by_slug(course_slug)
            if course is None:
                raise NotFoundError("course not found")
            module = await uow.modules.get_by_slug(course.id, module_slug)
            if module is None:
                raise NotFoundError("module not found")
            section = await uow.sections.get_by_slug(module.id, section_slug)
            if section is None:
                raise NotFoundError("quiz section not found")
            quiz = await uow.quizzes.get_by_section(section.id)
            if quiz is None:
                raise NotFoundError("quiz not found")
            results = await uow.sittings.list_final_results(quiz.id, learner_id)
            canonical = max(results, key=lambda result: result.total_score, default=None)
            return QuizResultSummaryDTO(quiz_id=quiz.id, is_exam=quiz.is_exam, best_score=canonical.total_score if canonical else None, finalized_attempts=len(results), max_attempts=quiz.max_attempts if quiz.is_exam else None, result=self._result_dto(canonical) if canonical else None)

    async def _owned_sitting(self, uow, sitting_id: UUID, learner_id: str) -> QuizSitting:
        sitting = await uow.sittings.get_by_id(sitting_id)
        if sitting is None or sitting.learner_id != learner_id:
            raise NotFoundError("quiz sitting not found")
        return sitting

    @staticmethod
    def _require_draft(sitting: QuizSitting) -> None:
        if sitting.attempt_state is not QuizAttemptState.IN_PROGRESS:
            raise ValidationError("quiz sitting is already final")

    @staticmethod
    def _draft_from_snapshot(sitting: QuizSitting, snapshot: list[QuizSittingQuestionSnapshot]) -> QuizSittingDraftDTO:
        return QuizSittingDraftDTO(id=sitting.id, quiz_id=sitting.quiz_id, attempt_state=str(sitting.attempt_state), available_question_codes=tuple(str(question.question_code) for question in snapshot))

    async def _draft_dto(self, uow, sitting: QuizSitting) -> QuizSittingDraftDTO:
        return self._draft_from_snapshot(sitting, await uow.sittings.get_snapshot(sitting.id))

    @staticmethod
    def _result_dto(result: QuizSittingResult) -> QuizSittingResultDTO:
        return QuizSittingResultDTO(
            id=result.sitting_id,
            quiz_id=result.quiz_id,
            attempt_state="GRADED",
            available_question_codes=tuple(str(code) for code in result.available_question_codes),
            question_answer=tuple(str(code) for code in result.question_answer),
            question_wrong=tuple(str(code) for code in result.question_wrong),
            question_unanswered=tuple(str(code) for code in result.question_unanswered),
            question_scores=tuple(QuestionScoreDTO(question_code=str(item.question_code), score=item.score) for item in result.question_results),
            total_score=result.total_score,
            finalized_at=result.finalized_at,
        )
