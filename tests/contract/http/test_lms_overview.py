from uuid import uuid4

import httpx
from sqlmodel import select

from app.application.ports.auth import CurrentUser
from app.domain.entities.course import Course
from app.domain.entities.module import Module
from app.domain.entities.quiz import Quiz
from app.domain.entities.section import Section
from app.domain.value_objects.content import ContentStatus, SectionContentType
from app.infrastructure.database.dependencies import get_uow
from app.infrastructure.persistence.models.collect_task import CollectTask as CollectTaskRow
from app.infrastructure.persistence.models.enrollment import Enrollment as EnrollmentRow
from app.infrastructure.persistence.models.quiz import Quiz as QuizRow
from app.infrastructure.persistence.models.quiz_sitting import QuizSitting as QuizSittingRow
from app.infrastructure.persistence.models.quiz_sitting_question import QuizSittingQuestion as SittingQuestionRow
from app.infrastructure.persistence.models.section_completion import SectionCompletion as CompletionRow
from app.infrastructure.persistence.unit_of_work import SqlModelUnitOfWork
from app.main import app
from app.presentation.dependencies.auth import get_current_user

ENDPOINT = "/api/admin/lms/overview"


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


async def _seed(session) -> None:
    """2 course (1 published), 3 enrollment, completion 1/2 published section, 4 task, sitting 3/4 soal."""
    course_published = Course(slug="ov-course-pub", title="Pub", status=ContentStatus.PUBLISHED)
    course_draft = Course(slug="ov-course-draft", title="Draft")
    module_pub = Module(slug="ov-m-pub", course_id=course_published.id, title="M1")
    module_draft = Module(slug="ov-m-draft", course_id=course_draft.id, title="M2")
    section_1 = Section(slug="ov-s-1", module_id=module_pub.id, title="S1", content_type=SectionContentType.QUIZ, position=0)  # hosts the quiz
    section_2 = Section(slug="ov-s-2", module_id=module_pub.id, title="S2", content_type=SectionContentType.MATERIAL, position=1)
    section_draft = Section(slug="ov-s-3", module_id=module_draft.id, title="S3", content_type=SectionContentType.MATERIAL, position=0)
    async with SqlModelUnitOfWork(session=session) as uow:
        await uow.courses.create(course_published)
        await uow.courses.create(course_draft)
        await uow.modules.create(module_pub)
        await uow.modules.create(module_draft)
        await uow.sections.create(section_1)
        await uow.sections.create(section_2)
        await uow.sections.create(section_draft)
        await uow.quizzes.create_quiz(Quiz(slug="ov-quiz", section_id=section_1.id))
        await uow.commit()

    quiz = (await session.exec(select(QuizRow).where(QuizRow.slug == "ov-quiz"))).one()
    submitted_at = course_published.created_at
    sitting = QuizSittingRow(
        slug="ov-sitting",
        quiz_id=quiz.id,
        learner_id="u-1",
        attempt_state="SUBMITTED",
        started_at=submitted_at,
        submitted_at=submitted_at,
        total_score=3,
    )
    session.add(EnrollmentRow(user_id="u-1", course_id=course_published.id, status="ENROLLED"))
    session.add(EnrollmentRow(user_id="u-2", course_id=course_published.id, status="COMPLETED"))
    session.add(EnrollmentRow(user_id="u-3", course_id=course_draft.id, status="WITHDRAWN"))
    session.add(CompletionRow(learner_id="u-1", section_id=section_1.id))
    session.add(CompletionRow(learner_id="u-1", section_id=section_draft.id))  # course draft: excluded
    # unique (learner_id, section_id) -> satu task per learner
    for learner_id, status in (
        ("u-1", "SUBMITTED"),
        ("u-2", "IN_REVIEW"),
        ("u-3", "REVIEWED"),
        ("u-4", "REVISION_REQUIRED"),
    ):
        session.add(CollectTaskRow(learner_id=learner_id, section_id=section_1.id, status=status))
    session.add(sitting)
    for position in range(4):
        session.add(
            SittingQuestionRow(
                sitting_id=sitting.id,
                source_question_id=uuid4(),
                question_code=f"Q-00000{position + 1}",
                prompt="?",
                question_type="MULTICHOICE",
                answer_policy="SINGLE",
                position=position,
            )
        )
    await session.commit()


async def test_overview_is_editor_only(session):
    client = await _client(session, _user("learner-1"))
    try:
        async with client:
            assert (await client.get(ENDPOINT)).status_code == 403
    finally:
        app.dependency_overrides.clear()


async def test_overview_returns_exact_kpis(session):
    await _seed(session)
    client = await _client(session, _user("guru-1", roles=("instructor",)))
    try:
        async with client:
            response = await client.get(ENDPOINT)
            assert response.status_code == 200, response.text
            data = response.json()["data"]
            assert set(data) == {
                "total_courses",
                "unique_learners",
                "active_enrollments",
                "pending_reviews",
                "section_completion_ratio",
                "avg_quiz_score_pct",
            }
            assert data["total_courses"] == 2
            assert data["unique_learners"] == 3
            assert data["active_enrollments"] == 1
            assert data["pending_reviews"] == 2
            assert data["section_completion_ratio"] == 50.0  # 1 completion / 2 published sections
            assert data["avg_quiz_score_pct"] == 75.0  # skor 3 / 4 soal
    finally:
        app.dependency_overrides.clear()
