from uuid import uuid4

import pytest

from app.domain.entities.quiz import Quiz
from app.domain.exceptions import ValidationError
from app.domain.value_objects.quiz_assessment import AnswerPolicy


def test_exam_defaults_to_one_and_non_exam_accepts_configured_value():
    quiz = Quiz(section_id=uuid4(), slug="quiz")
    quiz.configure_assessment(is_exam=True, max_attempts=None, answer_policy=AnswerPolicy.SINGLE)
    assert quiz.max_attempts == 1
    quiz.configure_assessment(is_exam=False, max_attempts=4, answer_policy=AnswerPolicy.MULTIPLE)
    assert quiz.is_exam is False
    assert quiz.max_attempts == 4


def test_attempt_limit_must_be_positive():
    with pytest.raises(ValidationError):
        Quiz(section_id=uuid4(), slug="quiz", max_attempts=0)
