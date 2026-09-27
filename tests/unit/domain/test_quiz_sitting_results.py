from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.domain.entities.quiz_sitting_snapshot import (
    QuizSittingOptionSnapshot,
    QuizSittingQuestionSnapshot,
    QuizSittingResult,
)
from app.domain.exceptions import ValidationError
from app.domain.services.quiz_evaluation import evaluate_snapshot_question
from app.domain.value_objects.quiz_assessment import AnswerPolicy, QuestionCode, QuestionResultOutcome


def snapshot(code: str = "Q-000001") -> QuizSittingQuestionSnapshot:
    return QuizSittingQuestionSnapshot(
        question_code=QuestionCode(code),
        prompt="Which are correct?",
        answer_policy=AnswerPolicy.MULTIPLE,
        options=(
            QuizSittingOptionSnapshot(value="A", position=0, is_correct=True),
            QuizSittingOptionSnapshot(value="B", position=1, is_correct=True),
            QuizSittingOptionSnapshot(value="C", position=2, is_correct=False),
        ),
    )


def test_multi_answer_requires_exact_set_and_result_partition_is_complete():
    first, second, third = snapshot(), snapshot("Q-000002"), snapshot("Q-000003")
    now = datetime.now(timezone.utc)
    correct = evaluate_snapshot_question(first, {first.options[0].id, first.options[1].id}, now)
    wrong = evaluate_snapshot_question(second, {second.options[0].id}, now)
    unanswered = evaluate_snapshot_question(third, set(), now)
    result = QuizSittingResult(
        sitting_id=uuid4(), quiz_id=uuid4(),
        available_question_codes=(first.question_code, second.question_code, third.question_code),
        question_results=(correct, wrong, unanswered), total_score=1, finalized_at=now,
    )
    assert result.question_answer == (QuestionCode("Q-000001"),)
    assert result.question_wrong == (QuestionCode("Q-000002"),)
    assert result.question_unanswered == (QuestionCode("Q-000003"),)
    assert {correct.outcome, wrong.outcome, unanswered.outcome} == {QuestionResultOutcome.ANSWERED, QuestionResultOutcome.WRONG, QuestionResultOutcome.UNANSWERED}


def test_result_rejects_missing_question_score():
    item = snapshot()
    now = datetime.now(timezone.utc)
    with pytest.raises(ValidationError, match="partition"):
        QuizSittingResult(sitting_id=uuid4(), quiz_id=uuid4(), available_question_codes=(item.question_code,), question_results=(), total_score=0, finalized_at=now)
