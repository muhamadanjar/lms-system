from uuid import uuid4

import pytest

from app.domain.entities.question import Question
from app.domain.exceptions import ValidationError
from app.domain.value_objects.content import ContentStatus
from app.domain.value_objects.quiz_assessment import QuestionCode


def test_question_code_normalizes_manual_input():
    assert QuestionCode(" q-network_01 ") == "Q-NETWORK_01"


def test_question_code_rejects_blank_and_published_changes():
    with pytest.raises(ValidationError):
        QuestionCode("  ")
    question = Question(quiz_id=uuid4(), slug="question", prompt="Prompt", question_code="q-1", status=ContentStatus.PUBLISHED)
    with pytest.raises(ValidationError, match="immutable"):
        question.change_question_code("Q-2")
