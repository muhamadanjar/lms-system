from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from app.domain.entities.base import ContentEntity
from app.domain.exceptions import ValidationError
from app.domain.value_objects.content import QuestionType, ensure_position, ensure_positive_weight, ensure_text

if TYPE_CHECKING:
    from app.domain.entities.answer import Answer


@dataclass
class Question(ContentEntity):
    quiz_id: UUID = field(default=None)  # type: ignore[assignment]
    prompt: str = ""
    question_type: QuestionType = QuestionType.MULTICHOICE
    weight: Decimal = Decimal("1")
    position: int = 0
    answers: list["Answer"] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.quiz_id is None:
            raise ValidationError("quiz_id is required")
        self.prompt = ensure_text(self.prompt, "prompt", 5000)
        self.question_type = QuestionType(self.question_type)
        self.weight = Decimal(str(ensure_positive_weight(self.weight)))
        self.position = ensure_position(self.position)
