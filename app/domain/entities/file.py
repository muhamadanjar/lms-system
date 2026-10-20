"""Metadata for a private file stored outside the relational database."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass(frozen=True)
class FileMetadata:
    id: UUID = field(default_factory=uuid4)
    original_filename: str = ""
    content_type: str = "application/octet-stream"
    size_bytes: int = 0
    storage_backend: str = "local"
    storage_key: str = ""
    sha256: str = ""
    uploaded_by: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
