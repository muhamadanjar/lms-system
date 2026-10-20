from collections.abc import Callable, Sequence
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import logging
from pathlib import PurePosixPath
from urllib.parse import quote
from uuid import UUID, uuid4

from app.application.dto.collect_task_review import CollectTaskReviewPage
from app.application.dto.review_notification import ReviewNotification
from app.application.dto.task_file_upload import MAX_TASK_FILES_PER_SUBMISSION, MAX_TASK_FILE_BYTES, MAX_TASK_SUBMISSION_BYTES, TaskFileUpload
from app.application.ports.auth import CurrentUser
from app.application.ports.file_storage import FileStoragePort
from app.application.ports.notification_publisher import NotificationPublisherPort
from app.domain.entities.collect_task import CollectTask, CollectTaskStatus
from app.domain.entities.course import Course
from app.domain.entities.file import FileMetadata
from app.domain.exceptions import AuthorizationError, NotFoundError, ValidationError
from app.domain.value_objects.content import ContentStatus, SectionContentType

logger = logging.getLogger(__name__)
STAGED_FILE_TTL = timedelta(hours=24)


class CollectTaskUseCases:
    """Application workflows for learner task submissions and administrator review."""

    def __init__(
        self,
        uow_factory: Callable,
        notification_publisher: NotificationPublisherPort | None = None,
    ):
        self.uow_factory = uow_factory
        self.notification_publisher = notification_publisher

    async def submit(self, actor: CurrentUser, course_slug: str, module_slug: str, section_slug: str, text: str, evidence_urls: Sequence[str], uploads: Sequence[TaskFileUpload] = (), file_storage: FileStoragePort | None = None, file_ids: Sequence[UUID] = ()) -> CollectTask:
        if uploads and file_ids:
            raise ValidationError("submit either uploaded files or staged file IDs, not both")
        if len(file_ids) > MAX_TASK_FILES_PER_SUBMISSION:
            raise ValidationError("at most 10 files may be submitted")
        if len(set(file_ids)) != len(file_ids):
            raise ValidationError("uploaded file IDs must be unique")
        safe_uploads = _validate_uploads(uploads)
        if safe_uploads and file_storage is None:
            raise ValidationError("file storage is not configured")
        stored: list[tuple[str, str]] = []
        metadata: list[FileMetadata] = []
        try:
            for upload, filename, content_type in safe_uploads:
                key = uuid4().hex
                assert file_storage is not None
                stored.append((file_storage.active_backend, key))
                await file_storage.put(key, upload.content, content_type)
                metadata.append(FileMetadata(original_filename=filename, content_type=content_type, size_bytes=len(upload.content), storage_backend=file_storage.active_backend, storage_key=key, sha256=sha256(upload.content).hexdigest(), uploaded_by=actor.id))
            async with self.uow_factory() as uow:
                course = await uow.courses.get_by_slug(course_slug)
                if course is None:
                    raise NotFoundError("course not found")
                module = await uow.modules.get_by_slug(course.id, module_slug)
                section = await uow.sections.get_by_slug(module.id, section_slug) if module else None
                if section is None or section.content_type is not SectionContentType.LAB_TASK:
                    raise NotFoundError("lab section not found")
                if course.status is not ContentStatus.PUBLISHED or module.status is not ContentStatus.PUBLISHED or section.status is not ContentStatus.PUBLISHED:
                    raise NotFoundError("lab section not found")
                await uow.lock_collect_task_submission(actor.id, course.id)
                enrollment = await uow.enrollments.get_live(actor.id, course.id)
                if enrollment is None:
                    raise AuthorizationError("active course enrollment is required")
                from app.application.use_cases.learner_progress import LearnerProgressUseCases
                await LearnerProgressUseCases(lambda: uow)._assert_section_access(uow, actor.id, course.id, section.id)
                if file_ids:
                    metadata = await uow.learning_progress.get_staged_files_for_submission(
                        list(file_ids), actor.id, datetime.now(timezone.utc)
                    )
                    if len(metadata) != len(file_ids):
                        raise ValidationError("one or more uploaded files are unavailable for this task")
                    if sum(item.size_bytes for item in metadata) > MAX_TASK_SUBMISSION_BYTES:
                        raise ValidationError("total uploaded file size must not exceed 100 MB")
                task = await uow.learning_progress.get_task(actor.id, section.id)
                if task is None:
                    task = CollectTask(learner_id=actor.id, section_id=section.id)
                before = len(task.history)
                task.submit(actor.id, text, evidence_urls, metadata)
                await uow.learning_progress.save_task(task, task.history[before:])
                await uow.commit()
                return task
        except Exception:
            if file_storage is not None:
                for backend, key in stored:
                    try:
                        await file_storage.delete(backend, key)
                    except Exception:
                        pass
            raise

    async def upload_file(
        self,
        actor: CurrentUser,
        course_slug: str,
        module_slug: str,
        section_slug: str,
        upload: TaskFileUpload,
        file_storage: FileStoragePort,
    ) -> FileMetadata:
        """Store one learner file and commit its metadata before task submission."""
        validated = _validate_uploads((upload,))
        safe_upload, filename, content_type = validated[0]
        key = uuid4().hex
        metadata = FileMetadata(
            original_filename=filename,
            content_type=content_type,
            size_bytes=len(safe_upload.content),
            storage_backend=file_storage.active_backend,
            storage_key=key,
            sha256=sha256(safe_upload.content).hexdigest(),
            uploaded_by=actor.id,
        )
        stored = False
        try:
            async with self.uow_factory() as uow:
                course, section = await _get_published_lab_section(
                    uow, course_slug, module_slug, section_slug
                )
                enrollment = await uow.enrollments.get_live(actor.id, course.id)
                if enrollment is None:
                    raise AuthorizationError("active course enrollment is required")
                from app.application.use_cases.learner_progress import LearnerProgressUseCases
                await LearnerProgressUseCases(lambda: uow)._assert_section_access(
                    uow, actor.id, course.id, section.id
                )
                await file_storage.put(key, safe_upload.content, content_type)
                stored = True
                await uow.learning_progress.save_staged_file(
                    metadata, metadata.created_at + STAGED_FILE_TTL
                )
                await uow.commit()
            return metadata
        except Exception:
            if stored:
                try:
                    await file_storage.delete(metadata.storage_backend, metadata.storage_key)
                except Exception:
                    logger.warning("Unable to remove object for a failed CollectTask upload")
            raise

    async def discard_uploaded_file(
        self,
        actor: CurrentUser,
        course_slug: str,
        module_slug: str,
        section_slug: str,
        file_id: UUID,
        file_storage: FileStoragePort,
    ) -> None:
        """Remove an owned staged file that has not been attached to a task."""
        async with self.uow_factory() as uow:
            await _get_lab_section(uow, course_slug, module_slug, section_slug)
            metadata = await uow.learning_progress.get_staged_file_for_deletion(
                file_id, actor.id
            )
            if metadata is None:
                raise NotFoundError("uploaded file not found")
            await file_storage.delete(metadata.storage_backend, metadata.storage_key)
            await uow.learning_progress.delete_staged_file(metadata.id)
            await uow.commit()

    async def cleanup_expired_uploads(self, file_storage: FileStoragePort) -> None:
        """Delete expired staged files that were never attached to a submission."""
        async with self.uow_factory() as uow:
            expired = await uow.learning_progress.list_expired_staged_files(datetime.now(timezone.utc))
            for metadata in expired:
                try:
                    await file_storage.delete(metadata.storage_backend, metadata.storage_key)
                except Exception:
                    logger.warning("Unable to remove an expired CollectTask upload object")
                    continue
                await uow.learning_progress.delete_staged_file(metadata.id)
            await uow.commit()

    async def mine(self, actor: CurrentUser, course_slug: str, module_slug: str, section_slug: str) -> CollectTask | None:
        async with self.uow_factory() as uow:
            course = await uow.courses.get_by_slug(course_slug)
            module = await uow.modules.get_by_slug(course.id, module_slug) if course else None
            section = await uow.sections.get_by_slug(module.id, section_slug) if module else None
            if section is None or section.content_type is not SectionContentType.LAB_TASK:
                raise NotFoundError("lab section not found")
            if course.status is not ContentStatus.PUBLISHED or module.status is not ContentStatus.PUBLISHED or section.status is not ContentStatus.PUBLISHED:
                raise NotFoundError("lab section not found")
            enrollments = await uow.enrollments.list_history(actor.id, course.id)
            if not enrollments:
                raise AuthorizationError("active course enrollment is required")
            task = await uow.learning_progress.get_task(actor.id, section.id)
            await uow.rollback()
            return task

    async def list_review_courses(self, actor: CurrentUser) -> list[Course]:
        self._require_admin(actor)
        async with self.uow_factory() as uow:
            courses: list[Course] = []
            if self._is_global_reviewer(actor):
                offset = 0
                while True:
                    batch = await uow.courses.list(include_archived=True, offset=offset, limit=200)
                    courses.extend(batch)
                    if len(batch) < 200:
                        break
                    offset += len(batch)
            else:
                assignments = await uow.course_instructors.list_for_user(actor.id)
                for assignment in assignments:
                    course = await uow.courses.get_by_id(assignment.course_id)
                    if course is not None:
                        courses.append(course)
            await uow.rollback()
            return sorted(courses, key=lambda course: course.title.casefold())

    async def list_for_review(
        self,
        actor: CurrentUser,
        statuses: CollectTaskStatus | list[CollectTaskStatus] | None = None,
        *,
        course_id: UUID | None = None,
        learner_ids: list[str] | None = None,
        learner_search: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> CollectTaskReviewPage:
        self._require_admin(actor)
        async with self.uow_factory() as uow:
            scope_ids = None
            if not self._is_global_reviewer(actor):
                assignments = await uow.course_instructors.list_for_user(actor.id)
                scope_ids = [assignment.course_id for assignment in assignments]
            selected_statuses = (
                [statuses]
                if isinstance(statuses, CollectTaskStatus)
                else statuses or [CollectTaskStatus.SUBMITTED, CollectTaskStatus.IN_REVIEW]
            )
            entries, total = await uow.learning_progress.list_tasks_for_review(
                statuses=[item.value for item in selected_statuses],
                course_id=course_id,
                learner_ids=learner_ids,
                learner_search=learner_search,
                course_scope_ids=scope_ids,
                offset=(page - 1) * per_page,
                limit=per_page,
            )
            await uow.rollback()
            return CollectTaskReviewPage(entries, total, page, per_page)

    async def review(self, actor: CurrentUser, task_id: UUID, action: str, *, score: int | None = None, note: str | None = None) -> CollectTask:
        self._require_admin(actor)
        async with self.uow_factory() as uow:
            task = await uow.learning_progress.get_task_by_id(task_id)
            if task is None:
                raise NotFoundError("collect task not found")
            section = await uow.sections.get_by_id(task.section_id)
            module = await uow.modules.get_by_id(section.module_id) if section else None
            course = await uow.courses.get_by_id(module.course_id) if module else None
            if section is None or module is None or course is None:
                raise NotFoundError("collect task course hierarchy not found")
            if not self._is_global_reviewer(actor) and not await uow.course_instructors.is_assigned(actor.id, course.id):
                raise AuthorizationError("instructor is not assigned to this course")

            before = len(task.history)
            if action == "IN_REVIEW":
                task.begin_review(actor.id)
            elif action == "REVISION_REQUIRED":
                task.request_revision(actor.id, note or "")
            elif action == "PASSED":
                if score is None:
                    raise ValidationError("score is required when passing a task")
                task.pass_task(actor.id, score, note)
            elif action == "REVIEWED":
                if score is None:
                    raise ValidationError("score is required when completing a task review")
                task.complete_review(actor.id, score, note)
            else:
                raise ValidationError("unsupported review action")
            await uow.learning_progress.save_task(task, task.history[before:])
            from app.application.use_cases.learner_progress import LearnerProgressUseCases
            await LearnerProgressUseCases(lambda: uow).refresh_self_learning_completion(uow, task.learner_id, module.course_id)

            notification = None
            if action in {"REVISION_REQUIRED", "REVIEWED", "PASSED"}:
                labels = {
                    "REVISION_REQUIRED": "Perlu revisi",
                    "REVIEWED": "Review selesai",
                    "PASSED": "Lulus",
                }
                details = [
                    f"Course: {course.title}",
                    f"Tugas: {section.title}",
                    f"Hasil: {labels[action]}",
                ]
                if score is not None:
                    details.append(f"Skor: {score}/100")
                if note and note.strip():
                    details.append(f"Catatan reviewer: {note.strip()}")
                review_event = task.history[-1]
                notification = ReviewNotification(
                    idempotency_key=str(review_event.id),
                    recipient_user_id=task.learner_id,
                    title=f"Hasil review tugas lab: {labels[action]}",
                    message="\n".join(details),
                    event_type=f"lms.lab_task.review.{action.lower()}",
                    action_url=(
                        f"/courses/{quote(str(course.slug), safe='')}/watch/section/"
                        f"{quote(str(section.slug), safe='')}"
                    ),
                    metadata={
                        "task_id": str(task.id),
                        "course_id": str(course.id),
                        "course_slug": str(course.slug),
                        "section_id": str(section.id),
                        "section_slug": str(section.slug),
                        "status": action,
                        "score": score,
                        "reviewer_id": actor.id,
                    },
                )
            await uow.commit()
            if notification is not None and self.notification_publisher is not None:
                try:
                    await self.notification_publisher.publish(notification)
                except Exception as error:
                    logger.warning(
                        "UserManagement review notification failed task_id=%s event=%s error=%s",
                        task.id,
                        action,
                        type(error).__name__,
                    )
            return task

    @staticmethod
    def _is_global_reviewer(actor: CurrentUser) -> bool:
        return actor.is_superuser or actor.has_any_role(("admin",))

    @staticmethod
    def _require_admin(actor: CurrentUser) -> None:
        if not actor.is_superuser and not actor.has_any_role(("admin", "instructor")):
            raise AuthorizationError("administrator or instructor role is required")

    async def read_file(self, actor: CurrentUser, file_id: UUID, file_storage: FileStoragePort) -> tuple[FileMetadata, bytes]:
        async with self.uow_factory() as uow:
            result = await uow.learning_progress.get_file_for_task(file_id)
            if result is None:
                raise NotFoundError("file not found")
            metadata, owners, course_ids = result
            permitted = actor.is_superuser or actor.id in owners or actor.has_any_role(("admin",))
            if not permitted and actor.has_any_role(("instructor",)):
                for course_id in course_ids:
                    if await uow.course_instructors.is_assigned(actor.id, course_id):
                        permitted = True
                        break
            if not permitted:
                raise AuthorizationError("file access is not permitted")
            await uow.rollback()
            content = await file_storage.get(metadata.storage_backend, metadata.storage_key)
            return metadata, content


_ALLOWED_FILE_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".txt": "text/plain",
    ".csv": "text/csv",
    ".zip": "application/zip",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}
def _validate_uploads(uploads: Sequence[TaskFileUpload]) -> list[tuple[TaskFileUpload, str, str]]:
    if len(uploads) > MAX_TASK_FILES_PER_SUBMISSION:
        raise ValidationError("at most 10 files may be submitted")
    total = 0
    result: list[tuple[TaskFileUpload, str, str]] = []
    for upload in uploads:
        filename = PurePosixPath(upload.filename.replace("\\", "/")).name
        if not filename or len(filename) > 255 or "\x00" in filename:
            raise ValidationError("uploaded filename is invalid")
        content_type = _ALLOWED_FILE_TYPES.get(PurePosixPath(filename).suffix.lower())
        if content_type is None:
            raise ValidationError("uploaded file type is not allowed")
        size = len(upload.content)
        if size < 1 or size > MAX_TASK_FILE_BYTES:
            raise ValidationError("each uploaded file must be between 1 byte and 25 MB")
        total += size
        if total > MAX_TASK_SUBMISSION_BYTES:
            raise ValidationError("total uploaded file size must not exceed 100 MB")
        _validate_file_signature(filename, upload.content)
        result.append((TaskFileUpload(filename=filename, content=upload.content), filename, content_type))
    return result


def _validate_file_signature(filename: str, content: bytes) -> None:
    suffix = PurePosixPath(filename).suffix.lower()
    if suffix == ".pdf" and not content.startswith(b"%PDF-"):
        raise ValidationError("uploaded PDF signature is invalid")
    if suffix == ".png" and not content.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValidationError("uploaded PNG signature is invalid")
    if suffix in {".jpg", ".jpeg"} and not content.startswith(b"\xff\xd8\xff"):
        raise ValidationError("uploaded JPEG signature is invalid")


async def _get_lab_section(uow, course_slug: str, module_slug: str, section_slug: str):
    course = await uow.courses.get_by_slug(course_slug)
    module = await uow.modules.get_by_slug(course.id, module_slug) if course else None
    section = await uow.sections.get_by_slug(module.id, section_slug) if module else None
    if section is None or section.content_type is not SectionContentType.LAB_TASK:
        raise NotFoundError("lab section not found")
    return section


async def _get_published_lab_section(uow, course_slug: str, module_slug: str, section_slug: str):
    course = await uow.courses.get_by_slug(course_slug)
    module = await uow.modules.get_by_slug(course.id, module_slug) if course else None
    section = await uow.sections.get_by_slug(module.id, section_slug) if module else None
    if section is None or section.content_type is not SectionContentType.LAB_TASK:
        raise NotFoundError("lab section not found")
    if course.status is not ContentStatus.PUBLISHED or module.status is not ContentStatus.PUBLISHED or section.status is not ContentStatus.PUBLISHED:
        raise NotFoundError("lab section not found")
    return course, section
    if suffix in {".docx", ".xlsx", ".pptx", ".zip"} and not content.startswith(b"PK\x03\x04"):
        raise ValidationError("uploaded archive signature is invalid")
    if suffix in {".txt", ".csv"}:
        try:
            content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValidationError("uploaded text file must use UTF-8 encoding") from exc
        if b"\x00" in content:
            raise ValidationError("uploaded text file contains invalid binary data")
