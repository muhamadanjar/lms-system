from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from app.domain.entities.base import ContentEntity
from app.domain.exceptions import ValidationError
from app.domain.value_objects.content import SectionContentType, ensure_position, ensure_text

if TYPE_CHECKING:
    from app.domain.entities.course import Course
    from app.domain.entities.module import Module


@dataclass
class Section(ContentEntity):
    module_id: UUID = field(default=None)  # type: ignore[assignment]
    title: str = ""
    description: Optional[str] = None
    position: int = 0
    content_type: SectionContentType = SectionContentType.MATERIAL
    body: Optional[str] = None

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.module_id is None:
            raise ValidationError("module_id is required")
        self.title = ensure_text(self.title, "title", 255)
        self.position = ensure_position(self.position)
        self.content_type = SectionContentType(self.content_type)
        if self.description is not None:
            self.description = self.description.strip()

    def rename(self, title: str, description: Optional[str] = None) -> None:
        self.title = ensure_text(title, "title", 255)
        self.description = description.strip() if description is not None else None
        self.touch()

    def change_position(self, position: int) -> None:
        self.position = ensure_position(position)
        self.touch()


@dataclass
class CourseHierarchy:
    course: "Course"
    modules: list["Module"] = field(default_factory=list)
    sections_by_module: dict[UUID, list[Section]] = field(default_factory=dict)
