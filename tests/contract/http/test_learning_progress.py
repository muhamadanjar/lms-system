import httpx
from decimal import Decimal

from app.application.ports.auth import CurrentUser
from app.application.dto.quiz_sittings import AnswerSelectionInput
from app.application.use_cases.quiz_sittings import QuizSittingUseCases
from app.domain.entities.answer import Answer
from app.domain.entities.course import Course
from app.domain.entities.enrollment import Enrollment
from app.domain.entities.module import Module
from app.domain.entities.question import Question
from app.domain.entities.quiz import KnowledgeQuiz
from app.domain.entities.section import Section
from app.domain.value_objects.content import ContentStatus, SectionContentType
from app.domain.value_objects.learning_policy import CompletionMode, ProgressionMode
from app.domain.value_objects.content import QuestionType
from app.infrastructure.database.dependencies import get_uow
from app.infrastructure.notifications.dependencies import get_user_management_notification_publisher
from app.infrastructure.persistence.unit_of_work import SqlModelUnitOfWork
from app.infrastructure.storage.dependencies import get_file_storage
from app.infrastructure.storage.file_storage import ConfiguredFileStorage
from app.config.file_storage import FileStorageSettings
from app.main import app
from app.presentation.dependencies.auth import get_current_user


async def test_sequential_access_hides_locked_body_until_material_is_completed(session):
    learner = CurrentUser(id="learner-1", email="learner@example.com", roles=frozenset({"learner"}))
    course = Course(title="Sequential", slug="sequential", status=ContentStatus.PUBLISHED, progression_mode=ProgressionMode.SEQUENTIAL, completion_mode=CompletionMode.ADMIN_REVIEW)
    module = Module(course_id=course.id, title="Module", slug="module", status=ContentStatus.PUBLISHED)
    first = Section(module_id=module.id, title="First", slug="first", position=0, status=ContentStatus.PUBLISHED, body="First text")
    later = Section(module_id=module.id, title="Later", slug="later", position=1, status=ContentStatus.PUBLISHED, body="Locked text")
    async with SqlModelUnitOfWork(session=session) as uow:
        await uow.courses.create(course)
        await uow.modules.create(module)
        await uow.sections.create(first)
        await uow.sections.create(later)
        await uow.enrollments.create(Enrollment(user_id=learner.id, course_id=course.id))
        await uow.commit()

    async def override_uow():
        yield SqlModelUnitOfWork(session=session)

    async def override_user():
        return learner

    app.dependency_overrides[get_uow] = override_uow
    app.dependency_overrides[get_current_user] = override_user
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            listing = await client.get("/api/courses/sequential/modules/module/sections")
            rows = listing.json()["data"]
            assert rows[0]["is_accessible"] is True
            assert rows[1]["is_accessible"] is False
            assert rows[1]["body"] is None

            course_detail = await client.get("/api/courses/sequential")
            module_detail = await client.get("/api/courses/sequential/modules/module")
            assert course_detail.json()["data"]["modules"][0]["sections"][1]["body"] is None
            assert course_detail.json()["data"]["modules"][0]["sections"][1]["is_accessible"] is False
            assert module_detail.json()["data"]["sections"][1]["body"] is None

            locked = await client.get("/api/courses/sequential/modules/module/sections/later")
            assert locked.status_code == 422
            assert "Locked text" not in locked.text

            completed = await client.post("/api/courses/sequential/modules/module/sections/first/complete")
            assert completed.status_code == 200
            unlocked = await client.get("/api/courses/sequential/modules/module/sections/later")
            assert unlocked.status_code == 200
            assert unlocked.json()["data"]["body"] == "Locked text"
    finally:
        app.dependency_overrides.clear()


async def test_course_watch_resume_position_round_trips_and_rejects_locked_sections(session):
    learner = CurrentUser(id="resume-learner", email="resume@example.com", roles=frozenset({"learner"}))
    actor = {"user": learner}
    course = Course(
        title="Resume course",
        slug="resume-course",
        status=ContentStatus.PUBLISHED,
        progression_mode=ProgressionMode.SEQUENTIAL,
        completion_mode=CompletionMode.ADMIN_REVIEW,
    )
    module = Module(course_id=course.id, title="Module", slug="resume-module", status=ContentStatus.PUBLISHED)
    first = Section(module_id=module.id, title="First", slug="first-section", position=0, status=ContentStatus.PUBLISHED)
    locked = Section(module_id=module.id, title="Locked", slug="locked-section", position=1, status=ContentStatus.PUBLISHED)
    async with SqlModelUnitOfWork(session=session) as uow:
        await uow.courses.create(course)
        await uow.modules.create(module)
        await uow.sections.create(first)
        await uow.sections.create(locked)
        await uow.enrollments.create(Enrollment(user_id=learner.id, course_id=course.id))
        await uow.commit()

    async def override_uow():
        yield SqlModelUnitOfWork(session=session)

    async def override_user():
        return actor["user"]

    app.dependency_overrides[get_uow] = override_uow
    app.dependency_overrides[get_current_user] = override_user
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            progress_url = "/api/learner/courses/resume-course/progress"
            position_url = f"{progress_url}/position"
            initial = await client.get(progress_url)
            assert initial.status_code == 200
            assert initial.json()["data"]["last_opened"] is None

            saved = await client.put(
                position_url,
                json={"module_slug": "resume-module", "section_slug": "first-section"},
            )
            assert saved.status_code == 200
            assert saved.json()["data"] == {
                "module_slug": "resume-module",
                "section_slug": "first-section",
            }

            resumed = await client.get(progress_url)
            assert resumed.json()["data"]["last_opened"] == {
                "module_slug": "resume-module",
                "section_slug": "first-section",
            }

            rejected = await client.put(
                position_url,
                json={"module_slug": "resume-module", "section_slug": "locked-section"},
            )
            assert rejected.status_code == 422
            unchanged = await client.get(progress_url)
            assert unchanged.json()["data"]["last_opened"]["section_slug"] == "first-section"

            actor["user"] = CurrentUser(
                id="resume-instructor",
                email="instructor@example.com",
                roles=frozenset({"instructor"}),
            )
            denied = await client.put(
                position_url,
                json={"module_slug": "resume-module", "section_slug": "first-section"},
            )
            assert denied.status_code == 403
    finally:
        app.dependency_overrides.clear()


async def test_watch_position_is_isolated_per_learner(session):
    learner_a = CurrentUser(id="position-learner-a", email="a@example.com", roles=frozenset({"learner"}))
    learner_b = CurrentUser(id="position-learner-b", email="b@example.com", roles=frozenset({"learner"}))
    course = Course(title="Position course", slug="position-course", status=ContentStatus.PUBLISHED)
    module = Module(course_id=course.id, title="Module", slug="position-module", status=ContentStatus.PUBLISHED)
    first = Section(module_id=module.id, title="First", slug="position-first", position=0, status=ContentStatus.PUBLISHED)
    second = Section(module_id=module.id, title="Second", slug="position-second", position=1, status=ContentStatus.PUBLISHED)
    async with SqlModelUnitOfWork(session=session) as uow:
        await uow.courses.create(course)
        await uow.modules.create(module)
        await uow.sections.create(first)
        await uow.sections.create(second)
        await uow.enrollments.create(Enrollment(user_id=learner_a.id, course_id=course.id))
        await uow.enrollments.create(Enrollment(user_id=learner_b.id, course_id=course.id))
        await uow.commit()

    progress_url = "/api/learner/courses/position-course/progress"
    position_url = f"{progress_url}/position"

    async def override_uow():
        yield SqlModelUnitOfWork(session=session)

    async def as_learner_a():
        return learner_a

    async def as_learner_b():
        return learner_b

    app.dependency_overrides[get_uow] = override_uow
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            app.dependency_overrides[get_current_user] = as_learner_a
            saved = await client.put(position_url, json={"module_slug": "position-module", "section_slug": "position-first"})
            assert saved.status_code == 200

            app.dependency_overrides[get_current_user] = as_learner_b
            other = await client.get(progress_url)
            assert other.status_code == 200
            assert other.json()["data"]["last_opened"] is None

            saved_b = await client.put(position_url, json={"module_slug": "position-module", "section_slug": "position-second"})
            assert saved_b.status_code == 200

            app.dependency_overrides[get_current_user] = as_learner_a
            still_a = await client.get(progress_url)
            assert still_a.json()["data"]["last_opened"]["section_slug"] == "position-first"
    finally:
        app.dependency_overrides.clear()

async def test_sequential_access_continues_across_module_boundary(session):
    learner = CurrentUser(id="module-learner", email="module-learner@example.com", roles=frozenset({"learner"}))
    course = Course(title="Module sequence", slug="module-sequence", status=ContentStatus.PUBLISHED, progression_mode=ProgressionMode.SEQUENTIAL, completion_mode=CompletionMode.ADMIN_REVIEW)
    first_module = Module(course_id=course.id, title="First module", slug="first-module", position=0, status=ContentStatus.PUBLISHED)
    next_module = Module(course_id=course.id, title="Next module", slug="next-module", position=1, status=ContentStatus.PUBLISHED)
    first = Section(module_id=first_module.id, title="First material", slug="first-material", position=0, status=ContentStatus.PUBLISHED, body="Complete this first")
    later = Section(module_id=next_module.id, title="Later material", slug="later-material", position=0, status=ContentStatus.PUBLISHED, body="Locked across modules")
    async with SqlModelUnitOfWork(session=session) as uow:
        await uow.courses.create(course)
        await uow.modules.create(first_module)
        await uow.modules.create(next_module)
        await uow.sections.create(first)
        await uow.sections.create(later)
        await uow.enrollments.create(Enrollment(user_id=learner.id, course_id=course.id))
        await uow.commit()

    async def override_uow():
        yield SqlModelUnitOfWork(session=session)

    async def override_user():
        return learner

    app.dependency_overrides[get_uow] = override_uow
    app.dependency_overrides[get_current_user] = override_user
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            module_detail = await client.get("/api/courses/module-sequence/modules/next-module")
            section = module_detail.json()["data"]["sections"][0]
            assert section["is_accessible"] is False
            assert section["body"] is None

            blocked = await client.get("/api/courses/module-sequence/modules/next-module/sections/later-material")
            assert blocked.status_code == 422
            assert "Locked across modules" not in blocked.text

            completed = await client.post("/api/courses/module-sequence/modules/first-module/sections/first-material/complete")
            assert completed.status_code == 200
            unlocked = await client.get("/api/courses/module-sequence/modules/next-module/sections/later-material")
            assert unlocked.status_code == 200
            assert unlocked.json()["data"]["body"] == "Locked across modules"
    finally:
        app.dependency_overrides.clear()


async def test_collect_task_submission_review_and_self_learning_completion(session):
    learner = CurrentUser(id="learner-2", email="learner2@example.com", roles=frozenset({"learner"}))
    actor = {"user": learner}
    course = Course(title="Lab course", slug="lab-course", status=ContentStatus.PUBLISHED, completion_mode=CompletionMode.SELF_LEARNING)
    module = Module(course_id=course.id, title="Module", slug="lab-module", status=ContentStatus.PUBLISHED)
    lab = Section(module_id=module.id, title="Lab", slug="lab", status=ContentStatus.PUBLISHED, content_type=SectionContentType.LAB_TASK)
    async with SqlModelUnitOfWork(session=session) as uow:
        await uow.courses.create(course)
        await uow.modules.create(module)
        await uow.sections.create(lab)
        await uow.enrollments.create(Enrollment(user_id=learner.id, course_id=course.id))
        await uow.commit()

    async def override_uow():
        yield SqlModelUnitOfWork(session=session)

    async def override_user():
        return actor["user"]

    published_notifications = []

    class FakeNotificationPublisher:
        async def publish(self, notification):
            published_notifications.append(notification)

    async def override_notification_publisher():
        return FakeNotificationPublisher()

    app.dependency_overrides[get_uow] = override_uow
    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_user_management_notification_publisher] = override_notification_publisher
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/courses/lab-course/modules/lab-module/sections/lab/collect-task/submissions",
                json={"text": "Completed the lab", "evidence_urls": ["https://example.org/result"]},
            )
            assert response.status_code == 200
            task_id = response.json()["data"]["id"]
            actor["user"] = CurrentUser(id="admin-1", email="admin@example.com", roles=frozenset({"admin"}))
            review_url = f"/api/admin/collect-tasks/{task_id}/review"
            started = await client.post(review_url, json={"action": "IN_REVIEW"})
            assert started.status_code == 200
            reviewed = await client.post(review_url, json={"action": "REVIEWED", "score": 58})
            assert reviewed.status_code == 200
            assert reviewed.json()["data"]["status"] == "REVIEWED"
            assert len(reviewed.json()["data"]["history"]) == 3
            assert len(published_notifications) == 1
            assert published_notifications[0].event_type == "lms.lab_task.review.reviewed"
            assert published_notifications[0].idempotency_key

            actor["user"] = learner
            own = await client.get("/api/courses/lab-course/modules/lab-module/sections/lab/collect-task")
            assert own.status_code == 200
            assert own.json()["data"]["status"] == "REVIEWED"

        async with SqlModelUnitOfWork(session=session) as uow:
            history = await uow.enrollments.list_history(learner.id, course.id)
            assert history[0].status == "COMPLETED"
            await uow.rollback()
    finally:
        app.dependency_overrides.clear()


async def test_lab_submission_unlocks_next_section_before_review(session):
    learner = CurrentUser(id="lab-gate-learner", email="lab-gate@example.com", roles=frozenset({"learner"}))
    course = Course(
        title="Sequential lab course",
        slug="sequential-lab",
        status=ContentStatus.PUBLISHED,
        progression_mode=ProgressionMode.SEQUENTIAL,
        completion_mode=CompletionMode.ADMIN_REVIEW,
    )
    module = Module(course_id=course.id, title="Module", slug="lab-gate-module", status=ContentStatus.PUBLISHED)
    lab = Section(
        module_id=module.id,
        title="Lab",
        slug="lab-gate",
        position=0,
        status=ContentStatus.PUBLISHED,
        content_type=SectionContentType.LAB_TASK,
    )
    later = Section(
        module_id=module.id,
        title="Next",
        slug="after-lab",
        position=1,
        status=ContentStatus.PUBLISHED,
        body="Unlocked after submission",
    )
    async with SqlModelUnitOfWork(session=session) as uow:
        await uow.courses.create(course)
        await uow.modules.create(module)
        await uow.sections.create(lab)
        await uow.sections.create(later)
        await uow.enrollments.create(Enrollment(user_id=learner.id, course_id=course.id))
        await uow.commit()

    async def override_uow():
        yield SqlModelUnitOfWork(session=session)

    async def override_user():
        return learner

    app.dependency_overrides[get_uow] = override_uow
    app.dependency_overrides[get_current_user] = override_user
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            section_path = "/api/learner/courses/sequential-lab/modules/lab-gate-module/sections"
            locked = await client.get(f"{section_path}/after-lab")
            assert locked.status_code == 422

            submitted = await client.post(
                f"{section_path}/lab-gate/collect-task/submissions",
                json={"text": "Finished the Lab task", "evidence_urls": ["https://example.org/lab-result"]},
            )
            assert submitted.status_code == 200
            assert submitted.json()["data"]["status"] == "SUBMITTED"

            unlocked = await client.get(f"{section_path}/after-lab")
            assert unlocked.status_code == 200
            assert unlocked.json()["data"]["body"] == "Unlocked after submission"

            progress = await client.get("/api/learner/courses/sequential-lab/progress")
            assert progress.status_code == 200
            lab_progress = next(item for item in progress.json()["data"]["sections"] if item["section_slug"] == "lab-gate")
            assert lab_progress["is_accessible"] is True
            assert lab_progress["is_complete"] is False
    finally:
        app.dependency_overrides.clear()


async def test_collect_task_file_upload_keeps_revision_files_private_and_downloadable(session, tmp_path):
    learner = CurrentUser(id="upload-learner", email="upload@example.com", roles=frozenset({"learner"}))
    course = Course(title="Upload course", slug="upload-course", status=ContentStatus.PUBLISHED, completion_mode=CompletionMode.ADMIN_REVIEW)
    module = Module(course_id=course.id, title="Module", slug="upload-module", status=ContentStatus.PUBLISHED)
    lab = Section(module_id=module.id, title="Lab", slug="upload-lab", status=ContentStatus.PUBLISHED, content_type=SectionContentType.LAB_TASK)
    storage = ConfiguredFileStorage(FileStorageSettings(local_root=str(tmp_path)))
    async with SqlModelUnitOfWork(session=session) as uow:
        await uow.courses.create(course)
        await uow.modules.create(module)
        await uow.sections.create(lab)
        await uow.enrollments.create(Enrollment(user_id=learner.id, course_id=course.id))
        await uow.commit()

    async def override_uow():
        yield SqlModelUnitOfWork(session=session)

    async def override_user():
        return actor["user"]

    async def override_storage():
        return storage

    actor = {"user": learner}
    app.dependency_overrides[get_uow] = override_uow
    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_file_storage] = override_storage
    submit_url = "/api/courses/upload-course/modules/upload-module/sections/upload-lab/collect-task/submissions/files"
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            first = await client.post(submit_url, data={"text": "Initial upload"}, files={"files": ("first.txt", b"first file", "text/plain")})
            assert first.status_code == 200
            first_history = first.json()["data"]["history"][0]
            old_file = first_history["files"][0]
            assert old_file["filename"] == "first.txt"
            assert old_file["size_bytes"] == len(b"first file")

            task_id = first.json()["data"]["id"]
            review_url = f"/api/admin/collect-tasks/{task_id}/review"
            actor["user"] = CurrentUser(id="teacher-1", email="teacher@example.com", roles=frozenset({"instructor"}))
            assert (await client.post(review_url, json={"action": "IN_REVIEW"})).status_code == 200
            assert (await client.post(review_url, json={"action": "REVISION_REQUIRED", "note": "Upload a corrected file"})).status_code == 200

            actor["user"] = learner
            revised = await client.post(submit_url, data={"text": "Revised upload"}, files={"files": ("revised.pdf", b"%PDF-1.7 revised", "application/pdf")})
            assert revised.status_code == 200
            history = revised.json()["data"]["history"]
            assert history[0]["files"][0]["id"] == old_file["id"]
            new_file = history[-1]["files"][0]
            assert new_file["filename"] == "revised.pdf"

            download = await client.get(old_file["download_url"])
            assert download.status_code == 200
            assert download.content == b"first file"
            assert download.headers["cache-control"] == "private, no-store"

            actor["user"] = CurrentUser(id="other-learner", email="other@example.com", roles=frozenset({"learner"}))
            denied = await client.get(old_file["download_url"])
            assert denied.status_code == 403

            actor["user"] = CurrentUser(id="teacher-2", email="teacher2@example.com", roles=frozenset({"instructor"}))
            instructor_download = await client.get(new_file["download_url"])
            assert instructor_download.status_code == 200
            assert instructor_download.content == b"%PDF-1.7 revised"
    finally:
        app.dependency_overrides.clear()


async def test_failed_required_quiz_keeps_next_section_locked_until_retry_passes(session):
    learner = CurrentUser(id="quiz-learner", email="quiz-learner@example.com", roles=frozenset({"learner"}))
    course = Course(title="Quiz course", slug="quiz-course", status=ContentStatus.PUBLISHED, progression_mode=ProgressionMode.SEQUENTIAL, completion_mode=CompletionMode.ADMIN_REVIEW)
    module = Module(course_id=course.id, title="Module", slug="quiz-module", status=ContentStatus.PUBLISHED)
    quiz_section = Section(module_id=module.id, title="Required quiz", slug="required-quiz", position=0, status=ContentStatus.PUBLISHED, content_type=SectionContentType.QUIZ, requires_pass=True)
    later = Section(module_id=module.id, title="Next material", slug="next-material", position=1, status=ContentStatus.PUBLISHED, body="Next content")
    quiz = KnowledgeQuiz(course_id=course.id, section_id=quiz_section.id, title="Quiz", slug="quiz")
    question = Question(quiz_id=quiz.id, slug="question", prompt="Choose the correct option", question_type=QuestionType.MULTICHOICE, weight=Decimal("1"), question_code="q-required")
    correct = Answer(question_id=question.id, slug="correct", value="Correct", position=0, is_correct=True, question_type=QuestionType.MULTICHOICE)
    wrong = Answer(question_id=question.id, slug="wrong", value="Wrong", position=1, is_correct=False, question_type=QuestionType.MULTICHOICE)
    async with SqlModelUnitOfWork(session=session) as uow:
        await uow.courses.create(course)
        await uow.modules.create(module)
        await uow.sections.create(quiz_section)
        await uow.sections.create(later)
        await uow.quizzes.create_quiz(quiz)
        await uow.quizzes.create_question(question)
        await uow.quizzes.create_answer(correct)
        await uow.quizzes.create_answer(wrong)
        await uow.enrollments.create(Enrollment(user_id=learner.id, course_id=course.id))
        await uow.commit()

    async def override_uow():
        yield SqlModelUnitOfWork(session=session)

    async def override_user():
        return learner

    app.dependency_overrides[get_uow] = override_uow
    app.dependency_overrides[get_current_user] = override_user
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            locked = await client.get("/api/courses/quiz-course/modules/quiz-module/sections/next-material")
            assert locked.status_code == 422

            sittings = QuizSittingUseCases(SqlModelUnitOfWork(session=session))
            for should_pass in (False, True):
                draft, _ = await sittings.start_or_resume_for_path("quiz-course", "quiz-module", "required-quiz", learner.id)
                async with SqlModelUnitOfWork(session=session) as uow:
                    snapshot = await uow.sittings.get_snapshot(draft.id)
                    await uow.rollback()
                wanted_answer = correct.id if should_pass else wrong.id
                option_id = next(option.id for option in snapshot[0].options if option.source_answer_id == wanted_answer)
                await sittings.save_selections(draft.id, learner.id, (AnswerSelectionInput("Q-REQUIRED", (option_id,)),))
                await sittings.finalize(draft.id, learner.id)
                result = await client.get("/api/courses/quiz-course/modules/quiz-module/sections/next-material")
                assert result.status_code == (200 if should_pass else 422)
    finally:
        app.dependency_overrides.clear()


async def test_exam_section_does_not_lock_later_material(session):
    learner = CurrentUser(id="exam-learner", email="exam-learner@example.com", roles=frozenset({"learner"}))
    course = Course(title="Exam course", slug="exam-course", status=ContentStatus.PUBLISHED, progression_mode=ProgressionMode.SEQUENTIAL, completion_mode=CompletionMode.ADMIN_REVIEW)
    module = Module(course_id=course.id, title="Module", slug="exam-module", status=ContentStatus.PUBLISHED)
    exam_section = Section(module_id=module.id, title="Exam", slug="exam", position=0, status=ContentStatus.PUBLISHED, content_type=SectionContentType.QUIZ, requires_pass=True)
    later = Section(module_id=module.id, title="Next", slug="after-exam", position=1, status=ContentStatus.PUBLISHED, body="Available")
    exam = KnowledgeQuiz(course_id=course.id, section_id=exam_section.id, title="Exam", slug="exam-quiz", is_exam=True)
    async with SqlModelUnitOfWork(session=session) as uow:
        await uow.courses.create(course)
        await uow.modules.create(module)
        await uow.sections.create(exam_section)
        await uow.sections.create(later)
        await uow.quizzes.create_quiz(exam)
        await uow.enrollments.create(Enrollment(user_id=learner.id, course_id=course.id))
        await uow.commit()

    async def override_uow():
        yield SqlModelUnitOfWork(session=session)

    async def override_user():
        return learner

    app.dependency_overrides[get_uow] = override_uow
    app.dependency_overrides[get_current_user] = override_user
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/learner/courses/exam-course/modules/exam-module/sections/after-exam")
            assert response.status_code == 200
            assert response.json()["data"]["body"] == "Available"

            completed_material = await client.post(
                "/api/learner/courses/exam-course/modules/exam-module/sections/after-exam/complete"
            )
            assert completed_material.status_code == 200

            progress = await client.get("/api/learner/courses/exam-course/progress")
            assert progress.status_code == 200
            assert progress.json()["data"]["course_state"] == "PENDING_ADMIN_REVIEW"
    finally:
        app.dependency_overrides.clear()
