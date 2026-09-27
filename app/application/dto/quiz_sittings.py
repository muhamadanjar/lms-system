"""Framework-independent inputs and learner-safe quiz-sitting outputs."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class AnswerSelectionInput:
    question_code: str
    option_ids: tuple[UUID, ...]


@dataclass(frozen=True)
class QuestionScoreDTO:
    question_code: str
    score: int


@dataclass(frozen=True)
class QuizSittingResultDTO:
    id: UUID
    quiz_id: UUID
    attempt_state: str
    available_question_codes: tuple[str, ...]
    question_answer: tuple[str, ...]
    question_wrong: tuple[str, ...]
    question_unanswered: tuple[str, ...]
    question_scores: tuple[QuestionScoreDTO, ...]
    total_score: int
    finalized_at: datetime


@dataclass(frozen=True)
class QuizSittingDraftDTO:
    id: UUID
    quiz_id: UUID
    attempt_state: str
    available_question_codes: tuple[str, ...]


@dataclass(frozen=True)
class QuizResultSummaryDTO:
    quiz_id: UUID
    is_exam: bool
    best_score: int | None
    finalized_attempts: int
    max_attempts: int | None
    result: QuizSittingResultDTO | None
