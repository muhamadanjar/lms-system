"""Pure, deterministic evaluation of frozen multiple-choice snapshots."""

from datetime import datetime
from uuid import UUID

from app.domain.entities.quiz_sitting_snapshot import (
    QuizSittingQuestionResult,
    QuizSittingQuestionSnapshot,
)
from app.domain.value_objects.quiz_assessment import QuestionResultOutcome


def evaluate_snapshot_question(
    question: QuizSittingQuestionSnapshot,
    selected_option_ids: set[UUID],
    finalized_at: datetime,
) -> QuizSittingQuestionResult:
    """Evaluate one snapshot by exact option-id set equality.

    An empty set is explicitly unanswered; a partially-correct set is wrong.
    """

    valid_option_ids = {option.id for option in question.options}
    if not selected_option_ids.issubset(valid_option_ids):
        from app.domain.exceptions import ValidationError
        raise ValidationError("selected option does not belong to snapshot question")
    correct_option_ids = {option.id for option in question.options if option.is_correct}
    if not selected_option_ids:
        outcome, score = QuestionResultOutcome.UNANSWERED, 0
    elif selected_option_ids == correct_option_ids:
        outcome, score = QuestionResultOutcome.ANSWERED, 1
    else:
        outcome, score = QuestionResultOutcome.WRONG, 0
    return QuizSittingQuestionResult(
        sitting_question_id=question.id,
        question_code=question.question_code,
        outcome=outcome,
        score=score,
        finalized_at=finalized_at,
    )
