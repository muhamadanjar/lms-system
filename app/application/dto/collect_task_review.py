from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.entities.collect_task import CollectTask


@dataclass(frozen=True)
class CollectTaskReviewEntry:
    task: CollectTask
    course_id: UUID
    course_slug: str
    course_title: str
    module_slug: str
    module_title: str
    section_slug: str
    section_title: str
    latest_submission_at: datetime


@dataclass(frozen=True)
class CollectTaskReviewPage:
    items: list[CollectTaskReviewEntry]
    total: int
    page: int
    per_page: int
