import pytest

from app.domain.entities.quiz_sitting import QuizSitting
from app.domain.exceptions import InvalidTransitionError
from app.domain.value_objects.content import QuizAttemptState


def test_quiz_sitting_has_explicit_lifecycle():
    sitting = QuizSitting(quiz_id=__import__("uuid").uuid4(), learner_id="learner", slug="sitting")
    sitting.transition(QuizAttemptState.SUBMITTED)
    sitting.transition(QuizAttemptState.GRADED)
    with pytest.raises(InvalidTransitionError):
        sitting.transition(QuizAttemptState.IN_PROGRESS)
