from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.application.dto.quiz_sittings import QuizResultSummaryDTO, QuizSittingContentDTO, QuizSittingDraftDTO, QuizSittingResultDTO


class AnswerSelectionRequest(BaseModel):
    question_code: str = Field(min_length=1, max_length=80)
    option_ids: list[UUID] = Field(default_factory=list)

    @field_validator("option_ids")
    @classmethod
    def option_ids_must_be_unique(cls, values: list[UUID]) -> list[UUID]:
        if len(set(values)) != len(values):
            raise ValueError("option_ids must be unique")
        return values


class SaveSelectionsRequest(BaseModel):
    answers: list[AnswerSelectionRequest] = Field(default_factory=list)


class QuestionScoreRead(BaseModel):
    question_code: str
    score: int


class QuizSittingDraftRead(BaseModel):
    id: UUID
    quiz_id: UUID
    attempt_state: str
    available_question_codes: list[str]


class QuizSittingResultRead(QuizSittingDraftRead):
    question_answer: list[str]
    question_wrong: list[str]
    question_unanswered: list[str]
    question_scores: list[QuestionScoreRead]
    total_score: int
    finalized_at: datetime


class QuizSittingOptionRead(BaseModel):
    id: UUID
    value: str
    position: int


class QuizSittingQuestionRead(BaseModel):
    question_code: str
    prompt: str
    answer_policy: str
    position: int
    options: list[QuizSittingOptionRead]
    selected_option_ids: list[UUID]


class QuizSittingContentRead(BaseModel):
    id: UUID
    quiz_id: UUID
    attempt_state: str
    questions: list[QuizSittingQuestionRead]


class QuizResultSummaryRead(BaseModel):
    quiz_id: UUID
    is_exam: bool
    best_score: int | None
    best_percentage: float | None
    is_passed: bool | None
    finalized_attempts: int
    max_attempts: int | None
    result: QuizSittingResultRead | None


def draft_read(value: QuizSittingDraftDTO) -> QuizSittingDraftRead:
    return QuizSittingDraftRead(id=value.id, quiz_id=value.quiz_id, attempt_state=value.attempt_state, available_question_codes=list(value.available_question_codes))


def result_read(value: QuizSittingResultDTO, *, include_question_feedback: bool = True) -> QuizSittingResultRead:
    return QuizSittingResultRead(
        id=value.id,
        quiz_id=value.quiz_id,
        attempt_state=value.attempt_state,
        available_question_codes=list(value.available_question_codes) if include_question_feedback else [],
        question_answer=list(value.question_answer) if include_question_feedback else [],
        question_wrong=list(value.question_wrong) if include_question_feedback else [],
        question_unanswered=list(value.question_unanswered) if include_question_feedback else [],
        question_scores=[QuestionScoreRead(question_code=item.question_code, score=item.score) for item in value.question_scores] if include_question_feedback else [],
        total_score=value.total_score,
        finalized_at=value.finalized_at,
    )


def content_read(value: QuizSittingContentDTO) -> QuizSittingContentRead:
    return QuizSittingContentRead(
        id=value.id,
        quiz_id=value.quiz_id,
        attempt_state=value.attempt_state,
        questions=[
            QuizSittingQuestionRead(
                question_code=question.question_code,
                prompt=question.prompt,
                answer_policy=question.answer_policy,
                position=question.position,
                options=[QuizSittingOptionRead(id=option.id, value=option.value, position=option.position) for option in question.options],
                selected_option_ids=list(question.selected_option_ids),
            )
            for question in value.questions
        ],
    )


def summary_read(value: QuizResultSummaryDTO) -> QuizResultSummaryRead:
    return QuizResultSummaryRead(quiz_id=value.quiz_id, is_exam=value.is_exam, best_score=value.best_score, best_percentage=value.best_percentage, is_passed=value.is_passed, finalized_attempts=value.finalized_attempts, max_attempts=value.max_attempts, result=result_read(value.result, include_question_feedback=not value.is_exam) if value.result else None)
