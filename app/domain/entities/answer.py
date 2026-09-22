from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID

from app.domain.entities.base import ContentEntity
from app.domain.exceptions import ValidationError
from app.domain.value_objects.content import QuestionType, ensure_position, ensure_text


@dataclass
class Answer(ContentEntity):
    question_id: UUID = field(default=None)  # type: ignore[assignment]
    value: str = ""
    position: int = 0
    is_correct: Optional[bool] = None
    question_type: QuestionType = QuestionType.MULTICHOICE

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.question_id is None:
            raise ValidationError("question_id is required")
        self.value = ensure_text(self.value, "value", 5000)
        self.position = ensure_position(self.position)
        self.question_type = QuestionType(self.question_type)
        if self.question_type is QuestionType.MULTICHOICE and self.is_correct is None:
            raise ValidationError("MULTICHOICE answers require is_correct")
        if self.question_type is QuestionType.DIRECT and self.is_correct is not None:
            raise ValidationError("DIRECT answers do not accept is_correct")
