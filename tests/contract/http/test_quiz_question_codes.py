import httpx

from app.application.ports.auth import CurrentUser
from app.domain.entities.course import Course
from app.domain.entities.module import Module
from app.domain.entities.quiz import Quiz
from app.domain.entities.section import Section
from app.domain.value_objects.content import SectionContentType
from app.infrastructure.database.dependencies import get_uow
from app.infrastructure.persistence.unit_of_work import SqlModelUnitOfWork
from app.main import app
from app.presentation.dependencies.auth import get_current_user


async def test_author_can_create_normalized_or_generated_question_codes(session):
    course = Course(slug="code-course", title="Course")
    module = Module(slug="code-module", course_id=course.id, title="Module")
    section = Section(slug="code-section", module_id=module.id, title="Quiz", content_type=SectionContentType.QUIZ)
    quiz = Quiz(slug="code-quiz", section_id=section.id)
    async with SqlModelUnitOfWork(session=session) as uow:
        await uow.courses.create(course)
        await uow.modules.create(module)
        await uow.sections.create(section)
        await uow.quizzes.create_quiz(quiz)
        await uow.commit()

    async def override_uow():
        yield SqlModelUnitOfWork(session=session)

    async def override_user():
        return CurrentUser(id="author", roles=frozenset({"instructor"}))

    app.dependency_overrides[get_uow] = override_uow
    app.dependency_overrides[get_current_user] = override_user
    path = "/api/courses/code-course/modules/code-module/sections/code-section/quiz/questions"
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            manual = await client.post(path, json={"prompt": "Manual", "question_code": " q-manual-1 "})
            assert manual.status_code == 201
            assert manual.json()["data"]["question_code"] == "Q-MANUAL-1"
            duplicate = await client.post(path, json={"prompt": "Duplicate", "question_code": "Q-manual-1"})
            assert duplicate.status_code == 409
            assert duplicate.json()["error"]["code"] == "QUESTION_CODE_CONFLICT"
            generated = await client.post(path, json={"prompt": "Generated"})
            assert generated.status_code == 201
            assert generated.json()["data"]["question_code"] == "Q-000001"
    finally:
        app.dependency_overrides.clear()
