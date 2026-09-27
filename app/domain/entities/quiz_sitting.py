from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID

from app.domain.entities.base import ContentEntity
from app.domain.exceptions import InvalidTransitionError, ValidationError
from app.domain.value_objects.content import QuizAttemptState


@dataclass
class QuizSitting(ContentEntity):
    quiz_id: UUID = field(default=None)  # type: ignore[assignment]
    learner_id: str = ""
    attempt_state: QuizAttemptState = QuizAttemptState.IN_PROGRESS
    started_at: datetime = field(default=None)  # type: ignore[assignment]
    submitted_at: Optional[datetime] = None
    total_score: int | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.quiz_id is None or not self.learner_id.strip():
            raise ValidationError("quiz_id and learner_id are required")
        self.attempt_state = QuizAttemptState(self.attempt_state)
        if self.started_at is None:
            self.started_at = self.created_at
        if self.total_score is not None and (not isinstance(self.total_score, int) or self.total_score < 0):
            raise ValidationError("total_score must be a non-negative integer")

    def transition(self, target: QuizAttemptState) -> None:
        target = QuizAttemptState(target)
        allowed = {
            QuizAttemptState.IN_PROGRESS: {QuizAttemptState.SUBMITTED, QuizAttemptState.CANCELLED},
            QuizAttemptState.SUBMITTED: {QuizAttemptState.GRADED, QuizAttemptState.CANCELLED},
            QuizAttemptState.GRADED: set(),
            QuizAttemptState.CANCELLED: set(),
        }
        if target not in allowed[self.attempt_state]:
            raise InvalidTransitionError(f"cannot transition {self.attempt_state} to {target}")
        self.attempt_state = target
        if target is QuizAttemptState.SUBMITTED:
            self.submitted_at = self.updated_at
        self.touch()

    def finalize(self, total_score: int) -> None:
        """Apply the only supported final state change and freeze the score."""
        if self.attempt_state is QuizAttemptState.GRADED:
            if self.total_score != total_score:
                raise ValidationError("graded sitting is immutable")
            return
        if self.attempt_state is not QuizAttemptState.IN_PROGRESS:
            raise InvalidTransitionError("only an in-progress sitting may be finalized")
        if not isinstance(total_score, int) or total_score < 0:
            raise ValidationError("total_score must be a non-negative integer")
        self.transition(QuizAttemptState.SUBMITTED)
        self.total_score = total_score
        self.transition(QuizAttemptState.GRADED)
