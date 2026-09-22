from decimal import Decimal

from app.domain.entities.answer import Answer
from app.domain.entities.course import Course
from app.domain.entities.module import Module
from app.domain.entities.question import Question
from app.domain.entities.quiz import Quiz
from app.domain.entities.quiz_sitting import QuizSitting
from app.domain.entities.section import Section
from app.domain.value_objects.content import QuestionType, SectionContentType
from app.infrastructure.persistence.unit_of_work import SqlModelUnitOfWork


async def test_quiz_questions_answers_and_sitting(session):
    course = Course(slug="quiz-course", title="Quiz Course")
    module = Module(slug="quiz-module", course_id=course.id, title="Quiz Module")
    section = Section(slug="quiz-section", module_id=module.id, title="Quiz", content_type=SectionContentType.QUIZ)
    quiz = Quiz(slug="quiz", section_id=section.id)
    question = Question(slug="question", quiz_id=quiz.id, prompt="2 + 2?", question_type=QuestionType.MULTICHOICE, weight=Decimal("2"))
    answer = Answer(slug="answer", question_id=question.id, value="4", position=0, is_correct=True, question_type=QuestionType.MULTICHOICE)
    sitting = QuizSitting(slug="sitting", quiz_id=quiz.id, learner_id="learner-1")

    async with SqlModelUnitOfWork(session=session) as uow:
        await uow.courses.create(course)
        await uow.modules.create(module)
        await uow.sections.create(section)
        await uow.quizzes.create_quiz(quiz)
        await uow.quizzes.create_question(question)
        await uow.quizzes.create_answer(answer)
        await uow.sittings.create(sitting)
        await uow.commit()
    async with SqlModelUnitOfWork(session=session) as uow:
        questions = await uow.quizzes.list_questions(quiz.id)
        answers = await uow.quizzes.list_answers(questions[0])
        loaded = await uow.sittings.get_by_id(sitting.id)
        await uow.rollback()

    assert questions[0].weight == Decimal("2.0000")
    assert answers[0].is_correct is True
    assert loaded.attempt_state.value == "IN_PROGRESS"
