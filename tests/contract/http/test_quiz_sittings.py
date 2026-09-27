from decimal import Decimal

import httpx

from app.application.ports.auth import CurrentUser
from app.domain.entities.answer import Answer
from app.domain.entities.course import Course
from app.domain.entities.module import Module
from app.domain.entities.question import Question
from app.domain.entities.quiz import Quiz
from app.domain.entities.section import Section
from app.domain.value_objects.content import QuestionType, SectionContentType
from app.infrastructure.database.dependencies import get_uow
from app.infrastructure.persistence.unit_of_work import SqlModelUnitOfWork
from app.main import app
from app.presentation.dependencies.auth import get_current_user


async def test_learner_quiz_sitting_contract_never_leaks_answer_key(session):
    course = Course(slug="http-quiz-course", title="Course")
    module = Module(slug="http-quiz-module", course_id=course.id, title="Module")
    section = Section(slug="http-quiz-section", module_id=module.id, title="Quiz", content_type=SectionContentType.QUIZ)
    quiz = Quiz(slug="http-quiz", section_id=section.id)
    question = Question(slug="http-question", quiz_id=quiz.id, prompt="One?", question_type=QuestionType.MULTICHOICE, weight=Decimal("1"), question_code="q-http-1")
    answer = Answer(slug="http-answer", question_id=question.id, value="One", is_correct=True, question_type=QuestionType.MULTICHOICE)
    async with SqlModelUnitOfWork(session=session) as uow:
        await uow.courses.create(course)
        await uow.modules.create(module)
        await uow.sections.create(section)
        await uow.quizzes.create_quiz(quiz)
        await uow.quizzes.create_question(question)
        await uow.quizzes.create_answer(answer)
        await uow.commit()

    async def override_uow():
        yield SqlModelUnitOfWork(session=session)

    async def override_user():
        return CurrentUser(id="learner")

    app.dependency_overrides[get_uow] = override_uow
    app.dependency_overrides[get_current_user] = override_user
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            started = await client.post("/api/courses/http-quiz-course/modules/http-quiz-module/sections/http-quiz-section/quiz/sittings")
            assert started.status_code == 201
            sitting = started.json()["data"]
            assert sitting["available_question_codes"] == ["Q-HTTP-1"]
            assert "is_correct" not in str(sitting)
            async with SqlModelUnitOfWork(session=session) as uow:
                snapshot = await uow.sittings.get_snapshot(__import__("uuid").UUID(sitting["id"]))
                await uow.rollback()
            saved = await client.put(f"/api/quiz-sittings/{sitting['id']}/answers", json={"answers": [{"question_code": "Q-HTTP-1", "option_ids": [str(snapshot[0].options[0].id)]}]})
            assert saved.status_code == 200
            finalized = await client.post(f"/api/quiz-sittings/{sitting['id']}/finalize")
            assert finalized.status_code == 200
            body = finalized.json()["data"]
            assert body["question_answer"] == ["Q-HTTP-1"]
            assert body["total_score"] == 1
            assert "is_correct" not in str(body)
            mutation_after_final = await client.put(f"/api/quiz-sittings/{sitting['id']}/answers", json={"answers": []})
            assert mutation_after_final.status_code == 422
            assert mutation_after_final.json()["error"]["code"] == "VALIDATION_ERROR"
    finally:
        app.dependency_overrides.clear()
