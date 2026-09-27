from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from uuid import UUID

from app.domain.entities.base import ContentEntity
from app.domain.exceptions import ValidationError
from app.domain.value_objects.quiz_assessment import AnswerPolicy

if TYPE_CHECKING:
    from app.domain.entities.question import Question


@dataclass
class Quiz(ContentEntity):
    section_id: UUID = field(default=None)  # type: ignore[assignment]
    is_exam: bool = False
    max_attempts: int = 1
    answer_policy: AnswerPolicy = AnswerPolicy.SINGLE
    questions: list["Question"] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.section_id is None:
            raise ValidationError("section_id is required")
        self.answer_policy = AnswerPolicy(self.answer_policy)
        if not isinstance(self.max_attempts, int) or self.max_attempts < 1:
            raise ValidationError("max_attempts must be a positive integer")

    def configure_assessment(self, *, is_exam: bool, max_attempts: int | None, answer_policy: AnswerPolicy) -> None:
        """Set draft assessment policy; limits apply only when this is an exam."""
        if self.status.value == "PUBLISHED":
            raise ValidationError("published quiz assessment configuration is immutable")
        resolved_max_attempts = 1 if is_exam and max_attempts is None else (max_attempts or self.max_attempts)
        if not isinstance(resolved_max_attempts, int) or resolved_max_attempts < 1:
            raise ValidationError("max_attempts must be a positive integer")
        self.is_exam = is_exam
        self.max_attempts = resolved_max_attempts
        self.answer_policy = AnswerPolicy(answer_policy)
        self.touch()
