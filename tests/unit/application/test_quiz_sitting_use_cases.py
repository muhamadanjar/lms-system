from decimal import Decimal
from uuid import uuid4

import pytest

from app.application.dto.quiz_sittings import AnswerSelectionInput
from app.application.use_cases.quiz_sittings import QuizSittingUseCases
from app.domain.entities.answer import Answer
from app.domain.entities.question import Question
from app.domain.entities.quiz import Quiz
from app.domain.exceptions import NotFoundError, ValidationError
from app.domain.value_objects.content import QuestionType
from tests.unit.application.fakes import FakeQuizRepository, FakeQuizSittingUnitOfWork, FakeSittingRepository


def use_case():
    quiz = Quiz(section_id=uuid4(), slug="quiz")
    question = Question(quiz_id=quiz.id, slug="question", prompt="One?", question_type=QuestionType.MULTICHOICE, weight=Decimal("1"), question_code="q-1")
    answer = Answer(question_id=question.id, slug="answer", value="One", is_correct=True, question_type=QuestionType.MULTICHOICE)
    uow = FakeQuizSittingUnitOfWork(FakeQuizRepository(quiz, [question], {question.id: [answer]}), FakeSittingRepository())
    return QuizSittingUseCases(uow), uow


async def test_start_save_finalize_and_retry_are_idempotent():
    service, uow = use_case()
    draft, created = await service.start_or_resume(uow.quizzes.quiz.id, "learner")
    assert created is True
    snapshot = await uow.sittings.get_snapshot(draft.id)
    await service.save_selections(draft.id, "learner", (AnswerSelectionInput("Q-1", (snapshot[0].options[0].id,)),))
    final = await service.finalize(draft.id, "learner")
    retry = await service.finalize(draft.id, "learner")
    assert final == retry
    assert final.question_answer == ("Q-1",)
    assert uow.commits == 3


async def test_selection_and_ownership_errors_are_hidden_as_domain_errors():
    service, uow = use_case()
    draft, _ = await service.start_or_resume(uow.quizzes.quiz.id, "learner")
    with pytest.raises(NotFoundError):
        await service.get(draft.id, "another-learner")
    with pytest.raises(ValidationError):
        await service.save_selections(draft.id, "learner", (AnswerSelectionInput("Q-1", (uuid4(),)),))


async def test_direct_question_is_rejected_before_a_sitting_is_persisted():
    service, uow = use_case()
    uow.quizzes.questions[0].question_type = QuestionType.DIRECT
    with pytest.raises(ValidationError, match="DIRECT"):
        await service.start_or_resume(uow.quizzes.quiz.id, "learner")
    assert uow.sittings.sittings == {}
