import httpx

from app.application.ports.auth import CurrentUser
from app.infrastructure.database.dependencies import get_uow
from app.infrastructure.persistence.unit_of_work import SqlModelUnitOfWork
from app.main import app
from app.presentation.dependencies.auth import get_current_user


def _user(user_id: str, roles=("learner",)) -> CurrentUser:
    return CurrentUser(id=user_id, email=f"{user_id}@example.com", roles=frozenset(roles))


async def _client(session, user: CurrentUser):
    async def override_uow():
        yield SqlModelUnitOfWork(session=session)

    async def override_user():
        return user

    app.dependency_overrides[get_uow] = override_uow
    app.dependency_overrides[get_current_user] = override_user
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


def _as(user: CurrentUser):
    async def override_user():
        return user

    app.dependency_overrides[get_current_user] = override_user


async def _seed_quiz_section(client: httpx.AsyncClient) -> str:
    admin = _user("admin-1", roles=("admin",))
    _as(admin)
    assert (await client.post("/api/courses", json={"title": "Q", "slug": "quiz-guard-course"})).status_code == 201
    assert (await client.post("/api/courses/quiz-guard-course/modules", json={"title": "M", "slug": "quiz-guard-m"})).status_code == 201
    response = await client.post(
        "/api/courses/quiz-guard-course/modules/quiz-guard-m/sections",
        json={"title": "Quiz", "slug": "quiz-guard-s", "content_type": "QUIZ", "position": 0},
    )
    assert response.status_code == 201, response.text
    return "/api/courses/quiz-guard-course/modules/quiz-guard-m/sections/quiz-guard-s/quiz"


async def test_learner_denied_on_quiz_authoring(session):
    client = await _client(session, _user("admin-1", roles=("admin",)))
    try:
        async with client:
            base = await _seed_quiz_section(client)
            _as(_user("peserta-1"))
            assert (await client.patch(base, json={"is_exam": False})).status_code == 403
            assert (await client.post(f"{base}/questions", json={"prompt": "2+2?", "position": 0})).status_code == 403
            assert (await client.patch(f"{base}/questions/q-1", json={"question_code": "Q-000002"})).status_code == 403
    finally:
        app.dependency_overrides.clear()


async def test_editor_may_configure_quiz(session):
    from app.domain.entities.course import Course
    from app.domain.entities.module import Module
    from app.domain.entities.quiz import Quiz
    from app.domain.entities.section import Section
    from app.domain.value_objects.content import SectionContentType

    course = Course(slug="quiz-guard-course", title="Q")
    module = Module(slug="quiz-guard-m", course_id=course.id, title="M")
    section = Section(slug="quiz-guard-s", module_id=module.id, title="Quiz", content_type=SectionContentType.QUIZ)
    async with SqlModelUnitOfWork(session=session) as uow:
        await uow.courses.create(course)
        await uow.modules.create(module)
        await uow.sections.create(section)
        await uow.quizzes.create_quiz(Quiz(slug="quiz-guard", section_id=section.id))
        await uow.commit()

    client = await _client(session, _user("admin-1", roles=("admin",)))
    try:
        async with client:
            base = "/api/courses/quiz-guard-course/modules/quiz-guard-m/sections/quiz-guard-s/quiz"
            response = await client.patch(base, json={"is_exam": False})
            assert response.status_code == 200, response.text
    finally:
        app.dependency_overrides.clear()
