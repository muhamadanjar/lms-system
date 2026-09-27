"""Immutable learner-facing quiz-sitting snapshot entities.

Correctness is retained solely for deterministic server-side evaluation.  DTOs
must project ``QuizSittingResult`` rather than snapshot options.
"""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from app.domain.exceptions import ValidationError
from app.domain.value_objects.content import QuestionType
from app.domain.value_objects.quiz_assessment import AnswerPolicy, QuestionCode, QuestionResultOutcome


@dataclass(frozen=True)
class QuizSittingOptionSnapshot:
    id: UUID = field(default_factory=uuid4)
    source_answer_id: UUID = field(default_factory=uuid4)
    value: str = ""
    position: int = 0
    is_correct: bool = False

    def __post_init__(self) -> None:
        if not self.value.strip() or self.position < 0:
            raise ValidationError("snapshot option value and position are required")


@dataclass(frozen=True)
class QuizSittingQuestionSnapshot:
    id: UUID = field(default_factory=uuid4)
    sitting_id: UUID = field(default_factory=uuid4)
    source_question_id: UUID = field(default_factory=uuid4)
    question_code: QuestionCode = field(default_factory=lambda: QuestionCode("Q-000001"))
    prompt: str = ""
    question_type: QuestionType = QuestionType.MULTICHOICE
    answer_policy: AnswerPolicy = AnswerPolicy.SINGLE
    position: int = 0
    options: tuple[QuizSittingOptionSnapshot, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "question_code", QuestionCode(self.question_code))
        object.__setattr__(self, "question_type", QuestionType(self.question_type))
        object.__setattr__(self, "answer_policy", AnswerPolicy(self.answer_policy))
        if not self.prompt.strip() or self.position < 0:
            raise ValidationError("snapshot prompt and position are required")
        if self.question_type is not QuestionType.MULTICHOICE:
            raise ValidationError("only MULTICHOICE questions are supported in quiz sittings")
        if not self.options:
            raise ValidationError("snapshot questions require options")
        if len({option.position for option in self.options}) != len(self.options):
            raise ValidationError("snapshot option positions must be unique")
        if not any(option.is_correct for option in self.options):
            raise ValidationError("snapshot question requires a correct option")


@dataclass(frozen=True)
class QuizSittingQuestionResult:
    sitting_question_id: UUID
    question_code: QuestionCode
    outcome: QuestionResultOutcome
    score: int
    finalized_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "question_code", QuestionCode(self.question_code))
        object.__setattr__(self, "outcome", QuestionResultOutcome(self.outcome))
        if self.score not in (0, 1):
            raise ValidationError("multiple-choice question score must be 0 or 1")
        if (self.outcome is QuestionResultOutcome.ANSWERED) != (self.score == 1):
            raise ValidationError("answered result must have score 1 and other outcomes score 0")


@dataclass(frozen=True)
class QuizSittingResult:
    """Learner-safe immutable final projection."""

    sitting_id: UUID
    quiz_id: UUID
    available_question_codes: tuple[QuestionCode, ...]
    question_results: tuple[QuizSittingQuestionResult, ...]
    total_score: int
    finalized_at: datetime

    def __post_init__(self) -> None:
        codes = tuple(QuestionCode(code) for code in self.available_question_codes)
        object.__setattr__(self, "available_question_codes", codes)
        if len(set(codes)) != len(codes):
            raise ValidationError("available question codes must be unique")
        result_codes = {result.question_code for result in self.question_results}
        if result_codes != set(codes) or len(result_codes) != len(self.question_results):
            raise ValidationError("question results must partition available question codes")
        if self.total_score != sum(result.score for result in self.question_results):
            raise ValidationError("total_score must equal question-result scores")

    @property
    def question_answer(self) -> tuple[QuestionCode, ...]:
        return tuple(result.question_code for result in self.question_results if result.outcome is QuestionResultOutcome.ANSWERED)

    @property
    def question_wrong(self) -> tuple[QuestionCode, ...]:
        return tuple(result.question_code for result in self.question_results if result.outcome is QuestionResultOutcome.WRONG)

    @property
    def question_unanswered(self) -> tuple[QuestionCode, ...]:
        return tuple(result.question_code for result in self.question_results if result.outcome is QuestionResultOutcome.UNANSWERED)
