from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from uuid import UUID

from app.domain.entities.base import ContentEntity
from app.domain.exceptions import ValidationError

if TYPE_CHECKING:
    from app.domain.entities.question import Question


@dataclass
class Quiz(ContentEntity):
    section_id: UUID = field(default=None)  # type: ignore[assignment]
    questions: list["Question"] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.section_id is None:
            raise ValidationError("section_id is required")
