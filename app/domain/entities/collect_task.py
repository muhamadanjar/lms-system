from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Sequence
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from app.domain.exceptions import ValidationError
from app.domain.entities.file import FileMetadata


class CollectTaskStatus(StrEnum):
    SUBMITTED = "SUBMITTED"
    IN_REVIEW = "IN_REVIEW"
    REVISION_REQUIRED = "REVISION_REQUIRED"
    REVIEWED = "REVIEWED"
    PASSED = "PASSED"


@dataclass(frozen=True)
class CollectTaskEvent:
    task_id: UUID
    actor_id: str
    action: str
    status: CollectTaskStatus
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    id: UUID = field(default_factory=uuid4)
    submission_text: str | None = None
    evidence_urls: tuple[str, ...] = ()
    files: tuple[FileMetadata, ...] = ()
    score: int | None = None
    review_note: str | None = None


@dataclass
class CollectTask:
    """Current lab task state; each accepted transition emits a history event."""

    learner_id: str
    section_id: UUID
    id: UUID = field(default_factory=uuid4)
    status: CollectTaskStatus = CollectTaskStatus.SUBMITTED
    score: int | None = None
    review_note: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    history: list[CollectTaskEvent] = field(default_factory=list)

    def submit(self, actor_id: str, text: str, evidence_urls: Sequence[str], files: Sequence[FileMetadata] = ()) -> CollectTaskEvent:
        body = text.strip() if isinstance(text, str) else ""
        urls = tuple(_validate_evidence_url(value) for value in evidence_urls)
        if not body:
            raise ValidationError("submission text is required")
        if not urls and not files:
            raise ValidationError("at least one evidence URL or file is required")
        if self.history and self.status is not CollectTaskStatus.REVISION_REQUIRED:
            raise ValidationError("task can only be resubmitted when revision is required")
        self.status = CollectTaskStatus.SUBMITTED
        self.score = None
        self.review_note = None
        return self._record(CollectTaskEvent(self.id, actor_id, "SUBMISSION", self.status, submission_text=body, evidence_urls=urls, files=tuple(files)))

    def begin_review(self, reviewer_id: str) -> CollectTaskEvent:
        if self.status is not CollectTaskStatus.SUBMITTED:
            raise ValidationError("only submitted tasks can enter review")
        self.status = CollectTaskStatus.IN_REVIEW
        return self._record(CollectTaskEvent(self.id, reviewer_id, "REVIEW_STARTED", self.status))

    def request_revision(self, reviewer_id: str, note: str) -> CollectTaskEvent:
        feedback = note.strip() if isinstance(note, str) else ""
        if self.status is not CollectTaskStatus.IN_REVIEW:
            raise ValidationError("task must be in review before requesting revision")
        if not feedback:
            raise ValidationError("review note is required for revision")
        self.status = CollectTaskStatus.REVISION_REQUIRED
        self.review_note = feedback
        self.score = None
        return self._record(CollectTaskEvent(self.id, reviewer_id, "REVISION_REQUIRED", self.status, review_note=feedback))

    def pass_task(self, reviewer_id: str, score: int, note: str | None = None) -> CollectTaskEvent:
        if self.status is not CollectTaskStatus.IN_REVIEW:
            raise ValidationError("task must be in review before passing")
        _validate_score(score)
        self.status = CollectTaskStatus.PASSED
        self.score = score
        self.review_note = note.strip() if note and note.strip() else None
        return self._record(CollectTaskEvent(self.id, reviewer_id, "PASSED", self.status, score=score, review_note=self.review_note))

    def complete_review(self, reviewer_id: str, score: int, note: str | None = None) -> CollectTaskEvent:
        if self.status is not CollectTaskStatus.IN_REVIEW:
            raise ValidationError("task must be in review before completing review")
        _validate_score(score)
        self.status = CollectTaskStatus.REVIEWED
        self.score = score
        self.review_note = note.strip() if note and note.strip() else None
        return self._record(CollectTaskEvent(self.id, reviewer_id, "REVIEWED", self.status, score=score, review_note=self.review_note))

    def _record(self, event: CollectTaskEvent) -> CollectTaskEvent:
        self.updated_at = event.created_at
        self.history.append(event)
        return event


def _validate_score(score: int) -> None:
    if not isinstance(score, int) or isinstance(score, bool) or not 0 <= score <= 100:
        raise ValidationError("score must be an integer between 0 and 100")


def _validate_evidence_url(value: str) -> str:
    candidate = value.strip() if isinstance(value, str) else ""
    parsed = urlsplit(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
        raise ValidationError("evidence URL must use HTTP or HTTPS")
    return candidate
