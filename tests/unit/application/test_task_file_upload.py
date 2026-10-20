import pytest

from app.application.dto.task_file_upload import TaskFileUpload
from app.application.use_cases.collect_tasks import _validate_uploads
from app.domain.exceptions import ValidationError


def test_upload_validation_sanitizes_name_and_assigns_trusted_content_type():
    files = _validate_uploads([TaskFileUpload("../../answer.PDF", b"%PDF-1.7\ncontent")])
    upload, name, content_type = files[0]
    assert upload.filename == "answer.PDF"
    assert name == "answer.PDF"
    assert content_type == "application/pdf"


@pytest.mark.parametrize(
    "uploads",
    [
        [TaskFileUpload("script.exe", b"MZ")],
        [TaskFileUpload("fake.pdf", b"not a pdf")],
        [TaskFileUpload("empty.txt", b"")],
    ],
)
def test_upload_validation_rejects_disallowed_or_invalid_files(uploads):
    with pytest.raises(ValidationError):
        _validate_uploads(uploads)


def test_upload_validation_enforces_file_count():
    with pytest.raises(ValidationError, match="10 files"):
        _validate_uploads([TaskFileUpload(f"{index}.txt", b"valid") for index in range(11)])
