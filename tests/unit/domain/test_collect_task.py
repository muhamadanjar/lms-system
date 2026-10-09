from uuid import uuid4

import pytest

from app.domain.entities.collect_task import CollectTask, CollectTaskStatus
from app.domain.entities.file import FileMetadata
from app.domain.exceptions import ValidationError


def test_collect_task_submission_revision_and_review_history_are_preserved():
    task = CollectTask(learner_id="learner-1", section_id=uuid4())
    first = task.submit("learner-1", "First submission", ["https://example.com/one"])
    task.begin_review("admin-1")
    revision = task.request_revision("admin-1", "Please add detail")
    second = task.submit("learner-1", "Revised submission", ["http://example.com/two"])
    task.begin_review("admin-1")
    reviewed = task.complete_review("admin-1", 62, "Reviewed without revision")

    assert task.status is CollectTaskStatus.REVIEWED
    assert [event.action for event in task.history] == ["SUBMISSION", "REVIEW_STARTED", "REVISION_REQUIRED", "SUBMISSION", "REVIEW_STARTED", "REVIEWED"]
    assert first.submission_text == "First submission"
    assert revision.review_note == "Please add detail"
    assert second.evidence_urls == ("http://example.com/two",)
    assert reviewed.score == 62


@pytest.mark.parametrize("urls", [[], ["ftp://example.com/file"], ["/relative/path"]])
def test_collect_task_rejects_invalid_evidence_urls(urls):
    task = CollectTask(learner_id="learner-1", section_id=uuid4())
    with pytest.raises(ValidationError):
        task.submit("learner-1", "Submission", urls)


def test_collect_task_revision_requires_note_and_scores_are_bounded():
    task = CollectTask(learner_id="learner-1", section_id=uuid4())
    task.submit("learner-1", "Submission", ["https://example.com"])
    task.begin_review("admin-1")
    with pytest.raises(ValidationError, match="review note"):
        task.request_revision("admin-1", " ")
    with pytest.raises(ValidationError, match="score"):
        task.pass_task("admin-1", 101)


def test_collect_task_accepts_file_only_evidence_and_keeps_each_revision_file_set():
    task = CollectTask(learner_id="learner-1", section_id=uuid4())
    first_file = FileMetadata(original_filename="first.pdf", storage_key="first")
    first = task.submit("learner-1", "First submission", [], [first_file])
    task.begin_review("admin-1")
    task.request_revision("admin-1", "Upload a clearer file")
    revised_file = FileMetadata(original_filename="revised.pdf", storage_key="revised")
    second = task.submit("learner-1", "Revised submission", [], [revised_file])

    assert first.files == (first_file,)
    assert second.files == (revised_file,)
    assert first.id != second.id
