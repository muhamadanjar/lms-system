from decimal import Decimal

import pytest

from app.application.dto.quiz_sittings import AnswerSelectionInput
from app.application.use_cases.quiz_sittings import QuizSittingUseCases
from app.domain.entities.answer import Answer
from app.domain.entities.course import Course
from app.domain.entities.module import Module
from app.domain.entities.question import Question
from app.domain.entities.quiz import Quiz
from app.domain.entities.section import Section
from app.domain.exceptions import ConflictError
from app.domain.value_objects.content import QuestionType, SectionContentType
from app.infrastructure.persistence.unit_of_work import SqlModelUnitOfWork


async def test_exam_limit_applies_only_on_finalization(session):
    course = Course(slug="exam-course", title="Course")
    module = Module(slug="exam-module", course_id=course.id, title="Module")
    section = Section(slug="exam-section", module_id=module.id, title="Quiz", content_type=SectionContentType.QUIZ)
    quiz = Quiz(slug="exam-quiz", section_id=section.id, is_exam=True, max_attempts=1)
    question = Question(slug="exam-question", quiz_id=quiz.id, prompt="One?", question_type=QuestionType.MULTICHOICE, weight=Decimal("1"), question_code="q-exam")
    answer = Answer(slug="exam-answer", question_id=question.id, value="One", is_correct=True, question_type=QuestionType.MULTICHOICE)
    async with SqlModelUnitOfWork(session=session) as uow:
        await uow.courses.create(course); await uow.modules.create(module); await uow.sections.create(section)
        await uow.quizzes.create_quiz(quiz); await uow.quizzes.create_question(question); await uow.quizzes.create_answer(answer); await uow.commit()

    use_cases = QuizSittingUseCases(SqlModelUnitOfWork(session=session))
    first, _ = await use_cases.start_or_resume(quiz.id, "learner")
    async with SqlModelUnitOfWork(session=session) as uow:
        option_id = (await uow.sittings.get_snapshot(first.id))[0].options[0].id
        await uow.rollback()
    await use_cases.save_selections(first.id, "learner", (AnswerSelectionInput("Q-EXAM", (option_id,)),))
    await use_cases.finalize(first.id, "learner")
    second, _ = await use_cases.start_or_resume(quiz.id, "learner")
    with pytest.raises(ConflictError, match="EXAM_ATTEMPT_LIMIT_REACHED"):
        await use_cases.finalize(second.id, "learner")
