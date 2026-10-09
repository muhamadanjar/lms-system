from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass(frozen=True)
class SectionCompletion:
    learner_id: str
    section_id: UUID
    id: UUID = field(default_factory=uuid4)
    completed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
