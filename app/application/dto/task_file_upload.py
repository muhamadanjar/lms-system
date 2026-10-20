"""Validated-at-boundary input for a task evidence upload."""

from dataclasses import dataclass

MAX_TASK_FILE_BYTES = 25_000_000
MAX_TASK_SUBMISSION_BYTES = 100_000_000
MAX_TASK_FILES_PER_SUBMISSION = 10


@dataclass(frozen=True)
class TaskFileUpload:
    filename: str
    content: bytes
