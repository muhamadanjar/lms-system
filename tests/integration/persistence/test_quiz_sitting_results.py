from decimal import Decimal

from app.application.dto.quiz_sittings import AnswerSelectionInput
from app.application.use_cases.quiz_sittings import QuizSittingUseCases
from app.domain.entities.answer import Answer
from app.domain.entities.course import Course
from app.domain.entities.module import Module
from app.domain.entities.question import Question
from app.domain.entities.quiz import Quiz
from app.domain.entities.section import Section
from app.domain.value_objects.content import QuestionType, SectionContentType
from app.domain.value_objects.quiz_assessment import AnswerPolicy
from app.infrastructure.persistence.unit_of_work import SqlModelUnitOfWork


async def test_snapshot_finalization_is_immutable_and_idempotent(session):
    course = Course(slug="result-course", title="Course")
    module = Module(slug="result-module", course_id=course.id, title="Module")
    section = Section(slug="result-section", module_id=module.id, title="Quiz", content_type=SectionContentType.QUIZ)
    quiz = Quiz(slug="result-quiz", section_id=section.id, answer_policy=AnswerPolicy.SINGLE)
    question = Question(slug="result-question", quiz_id=quiz.id, prompt="Correct?", question_type=QuestionType.MULTICHOICE, weight=Decimal("1"), question_code="q-1")
    correct = Answer(slug="result-correct", question_id=question.id, value="Yes", is_correct=True, question_type=QuestionType.MULTICHOICE)
    wrong = Answer(slug="result-wrong", question_id=question.id, value="No", position=1, is_correct=False, question_type=QuestionType.MULTICHOICE)
    async with SqlModelUnitOfWork(session=session) as uow:
        await uow.courses.create(course)
        await uow.modules.create(module)
        await uow.sections.create(section)
        await uow.quizzes.create_quiz(quiz)
        await uow.quizzes.create_question(question)
        await uow.quizzes.create_answer(correct)
        await uow.quizzes.create_answer(wrong)
        await uow.commit()

    uow = SqlModelUnitOfWork(session=session)
    use_cases = QuizSittingUseCases(uow)
    draft, created = await use_cases.start_or_resume(quiz.id, "learner")
    assert created is True
    async with uow:
        snapshot = await uow.sittings.get_snapshot(draft.id)
        await uow.rollback()
    await use_cases.save_selections(draft.id, "learner", (AnswerSelectionInput(question_code="q-1", option_ids=(snapshot[0].options[0].id,)),))
    result = await use_cases.finalize(draft.id, "learner")
    retry = await use_cases.finalize(draft.id, "learner")
    assert result.total_score == retry.total_score == 1
    assert result.question_answer == ("Q-1",)
    assert result.question_wrong == ()
    assert result.question_unanswered == ()
