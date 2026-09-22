from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.value_objects.content import ContentStatus, SectionContentType

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


class CourseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    slug: str = Field(min_length=1, max_length=160)
    status: ContentStatus = ContentStatus.DRAFT


class CourseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    slug: str | None = Field(default=None, min_length=1, max_length=160)
    status: ContentStatus | None = None


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


class SectionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    slug: str | None = Field(default=None, min_length=1, max_length=160)
    position: int | None = Field(default=None, ge=0)
    status: ContentStatus | None = None
    content_type: SectionContentType | None = None
    body: str | None = None


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
    created_at: datetime
    updated_at: datetime
    modules: list[ModuleRead] = Field(default_factory=list)


def section_read(section) -> SectionRead:
    return SectionRead.model_validate(section)


def module_read(module, sections=()) -> ModuleRead:
    return ModuleRead.model_validate({**module.__dict__, "sections": [section_read(section) for section in sections]})


def course_read(course, modules=(), sections_by_module=None) -> CourseRead:
    sections_by_module = sections_by_module or {}
    return CourseRead.model_validate({
        **course.__dict__,
        "modules": [module_read(module, sections_by_module.get(module.id, ())) for module in modules],
    })
