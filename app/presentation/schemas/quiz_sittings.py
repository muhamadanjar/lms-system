from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.application.dto.quiz_sittings import QuizResultSummaryDTO, QuizSittingDraftDTO, QuizSittingResultDTO


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


class QuizResultSummaryRead(BaseModel):
    quiz_id: UUID
    is_exam: bool
    best_score: int | None
    finalized_attempts: int
    max_attempts: int | None
    result: QuizSittingResultRead | None


def draft_read(value: QuizSittingDraftDTO) -> QuizSittingDraftRead:
    return QuizSittingDraftRead(id=value.id, quiz_id=value.quiz_id, attempt_state=value.attempt_state, available_question_codes=list(value.available_question_codes))


def result_read(value: QuizSittingResultDTO) -> QuizSittingResultRead:
    return QuizSittingResultRead(id=value.id, quiz_id=value.quiz_id, attempt_state=value.attempt_state, available_question_codes=list(value.available_question_codes), question_answer=list(value.question_answer), question_wrong=list(value.question_wrong), question_unanswered=list(value.question_unanswered), question_scores=[QuestionScoreRead(question_code=item.question_code, score=item.score) for item in value.question_scores], total_score=value.total_score, finalized_at=value.finalized_at)


def summary_read(value: QuizResultSummaryDTO) -> QuizResultSummaryRead:
    return QuizResultSummaryRead(quiz_id=value.quiz_id, is_exam=value.is_exam, best_score=value.best_score, finalized_attempts=value.finalized_attempts, max_attempts=value.max_attempts, result=result_read(value.result) if value.result else None)
