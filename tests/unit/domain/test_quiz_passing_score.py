import pytest
from uuid import uuid4

from app.domain.entities.quiz import KnowledgeQuiz
from app.domain.exceptions import ValidationError


def test_passing_score_defaults_to_seventy_and_can_be_changed():
    quiz = KnowledgeQuiz(course_id=uuid4(), slug="knowledge-check", title="Knowledge check")
    assert quiz.passing_score == 70
    quiz.set_passing_score(85)
    assert quiz.passing_score == 85


@pytest.mark.parametrize("score", [-1, 101, True, 70.5])
def test_passing_score_rejects_invalid_values(score):
    quiz = KnowledgeQuiz(course_id=uuid4(), slug="knowledge-check", title="Knowledge check")
    with pytest.raises(ValidationError, match="passing_score"):
        quiz.set_passing_score(score)
