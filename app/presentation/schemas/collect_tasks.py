from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl

from app.domain.entities.collect_task import CollectTask, CollectTaskEvent, CollectTaskStatus
from app.domain.entities.file import FileMetadata
from app.application.dto.collect_task_review import CollectTaskReviewEntry


class CollectTaskSubmissionRequest(BaseModel):
    text: str = Field(min_length=1, max_length=50000)
    evidence_urls: list[HttpUrl] = Field(default_factory=list, max_length=20)
    file_ids: list[UUID] = Field(default_factory=list, max_length=10)


class CollectTaskReviewRequest(BaseModel):
    action: str
    score: int | None = Field(default=None, ge=0, le=100)
    note: str | None = Field(default=None, max_length=10000)


class CollectTaskFileRead(BaseModel):
    id: UUID
    filename: str
    content_type: str
    size_bytes: int
    created_at: datetime
    download_url: str


class CollectTaskFileUploadRead(BaseModel):
    id: UUID
    filename: str
    content_type: str
    size_bytes: int
    created_at: datetime


class CollectTaskHistoryRead(BaseModel):
    actor_id: str
    action: str
    status: CollectTaskStatus
    created_at: datetime
    submission_text: str | None
    evidence_urls: list[str]
    score: int | None
    review_note: str | None
    files: list[CollectTaskFileRead] = Field(default_factory=list)


class CollectTaskRead(BaseModel):
    id: UUID
    learner_id: str
    section_id: UUID
    status: CollectTaskStatus
    score: int | None
    review_note: str | None
    created_at: datetime
    updated_at: datetime
    history: list[CollectTaskHistoryRead]


class CollectTaskReviewCourseRead(BaseModel):
    id: UUID
    slug: str
    title: str


class CollectTaskReviewItemRead(CollectTaskRead):
    course_id: UUID
    course_slug: str
    course_title: str
    module_slug: str
    module_title: str
    section_slug: str
    section_title: str
    latest_submission_at: datetime


def collect_task_read(task: CollectTask) -> CollectTaskRead:
    return CollectTaskRead(
        id=task.id, learner_id=task.learner_id, section_id=task.section_id, status=task.status,
        score=task.score, review_note=task.review_note, created_at=task.created_at,
        updated_at=task.updated_at, history=[collect_task_event_read(event) for event in task.history],
    )


def collect_task_review_read(entry: CollectTaskReviewEntry) -> CollectTaskReviewItemRead:
    values = collect_task_read(entry.task).model_dump()
    return CollectTaskReviewItemRead(
        **values,
        course_id=entry.course_id,
        course_slug=entry.course_slug,
        course_title=entry.course_title,
        module_slug=entry.module_slug,
        module_title=entry.module_title,
        section_slug=entry.section_slug,
        section_title=entry.section_title,
        latest_submission_at=entry.latest_submission_at,
    )


def collect_task_event_read(event: CollectTaskEvent) -> CollectTaskHistoryRead:
    return CollectTaskHistoryRead(
        actor_id=event.actor_id, action=event.action, status=event.status, created_at=event.created_at,
        submission_text=event.submission_text, evidence_urls=list(event.evidence_urls),
        score=event.score, review_note=event.review_note, files=[collect_task_file_read(item) for item in event.files],
    )


def collect_task_file_read(file: FileMetadata) -> CollectTaskFileRead:
    return CollectTaskFileRead(id=file.id, filename=file.original_filename, content_type=file.content_type, size_bytes=file.size_bytes, created_at=file.created_at, download_url=f"/api/files/{file.id}")


def collect_task_file_upload_read(file: FileMetadata) -> CollectTaskFileUploadRead:
    return CollectTaskFileUploadRead(id=file.id, filename=file.original_filename, content_type=file.content_type, size_bytes=file.size_bytes, created_at=file.created_at)
