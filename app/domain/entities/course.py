from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Optional

from app.domain.entities.base import ContentEntity
from app.domain.exceptions import ValidationError
from app.domain.value_objects.content import ensure_text

if TYPE_CHECKING:
    from app.domain.entities.module import Module


@dataclass
class Course(ContentEntity):
    title: str = ""
    description: Optional[str] = None
    modules: List["Module"] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        super().__post_init__()
        self.title = ensure_text(self.title, "title", 255)
        if self.description is not None:
            self.description = self.description.strip()

    def rename(self, title: str, description: Optional[str] = None) -> None:
        self.title = ensure_text(title, "title", 255)
        self.description = description.strip() if description is not None else None
        self.touch()
