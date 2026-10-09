from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.value_objects.content import ContentStatus, SectionContentType
from app.domain.value_objects.learning_policy import CompletionMode, ProgressionMode

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    data: T
    meta: dict[str, object] = Field(default_factory=dict)


class ErrorPayload(BaseModel):
    code: str
    message: str
    request_id: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorPayload


class PaginationQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    status: ContentStatus | None = None
    include_archived: bool = False
    search: str | None = Field(default=None, max_length=120)


class CourseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    slug: str = Field(min_length=1, max_length=160)
    status: ContentStatus = ContentStatus.DRAFT
    progression_mode: ProgressionMode = ProgressionMode.FREE
    completion_mode: CompletionMode = CompletionMode.SELF_LEARNING


class CourseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    slug: str | None = Field(default=None, min_length=1, max_length=160)
    status: ContentStatus | None = None
    progression_mode: ProgressionMode | None = None
    completion_mode: CompletionMode | None = None


class ModuleCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    slug: str = Field(min_length=1, max_length=160)
    position: int = Field(default=0, ge=0)
    status: ContentStatus = ContentStatus.DRAFT


class ModuleUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    slug: str | None = Field(default=None, min_length=1, max_length=160)
    status: ContentStatus | None = None
    position: int | None = Field(default=None, ge=0)


class SectionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    slug: str = Field(min_length=1, max_length=160)
    position: int = Field(default=0, ge=0)
    status: ContentStatus = ContentStatus.DRAFT
    content_type: SectionContentType = SectionContentType.MATERIAL
    body: str | None = None
    requires_pass: bool = False
    is_preview: bool = False
    terminal_enabled: bool = False


class SectionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    slug: str | None = Field(default=None, min_length=1, max_length=160)
    position: int | None = Field(default=None, ge=0)
    status: ContentStatus | None = None
    content_type: SectionContentType | None = None
    body: str | None = None
    requires_pass: bool | None = None
    is_preview: bool | None = None
    terminal_enabled: bool | None = None


class OrderItem(BaseModel):
    slug: str = Field(min_length=1, max_length=160)
    position: int = Field(ge=0)


class OrderRequest(BaseModel):
    items: list[OrderItem] = Field(min_length=1)

    @field_validator("items")
    @classmethod
    def positions_must_be_unique(cls, items: list[OrderItem]) -> list[OrderItem]:
        positions = {item.position for item in items}
        if len(positions) != len(items) or positions != set(range(len(items))):
            raise ValueError("positions must be unique and contiguous from zero")
        return items


class SectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    module_id: UUID
    slug: str
    title: str
    description: str | None
    position: int
    status: ContentStatus
    content_type: SectionContentType
    body: str | None
    requires_pass: bool = False
    is_preview: bool = False
    terminal_enabled: bool = False
    is_accessible: bool = True
    created_at: datetime
    updated_at: datetime


class ModuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    course_id: UUID
    slug: str
    title: str
    description: str | None
    position: int
    status: ContentStatus
    created_at: datetime
    updated_at: datetime
    sections: list[SectionRead] = Field(default_factory=list)


class CourseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    slug: str
    title: str
    description: str | None
    status: ContentStatus
    progression_mode: ProgressionMode = ProgressionMode.FREE
    completion_mode: CompletionMode = CompletionMode.SELF_LEARNING
    created_at: datetime
    updated_at: datetime
    modules: list[ModuleRead] = Field(default_factory=list)


def section_read(section, is_accessible: bool = True) -> SectionRead:
    return SectionRead.model_validate({**section.__dict__, "is_accessible": is_accessible})


def module_read(module, sections=(), access_by_id=None) -> ModuleRead:
    access_by_id = access_by_id or {}
    return ModuleRead.model_validate({**module.__dict__, "sections": [section_read(section, access_by_id.get(section.id, True)) for section in sections]})


def course_read(course, modules=(), sections_by_module=None, access_by_id=None) -> CourseRead:
    sections_by_module = sections_by_module or {}
    access_by_id = access_by_id or {}
    return CourseRead.model_validate({
        **course.__dict__,
        "modules": [module_read(module, sections_by_module.get(module.id, ()), access_by_id) for module in modules],
    })
