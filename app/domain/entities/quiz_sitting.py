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

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.quiz_id is None or not self.learner_id.strip():
            raise ValidationError("quiz_id and learner_id are required")
        self.attempt_state = QuizAttemptState(self.attempt_state)
        if self.started_at is None:
            self.started_at = self.created_at

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
