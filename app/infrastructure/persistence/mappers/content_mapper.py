from datetime import datetime, timezone

from app.domain.entities.course import Course
from app.domain.entities.module import Module
from app.domain.entities.section import Section
from app.domain.value_objects.content import ContentStatus, SectionContentType, Slug
from app.infrastructure.persistence.models.course import Course as CourseRow
from app.infrastructure.persistence.models.module import Module as ModuleRow
from app.infrastructure.persistence.models.section import Section as SectionRow


def utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def to_course(row: CourseRow) -> Course:
    return Course(
        id=row.id,
        slug=Slug(row.slug),
        status=ContentStatus(row.status),
        created_at=utc(row.created_at),
        updated_at=utc(row.updated_at),
        title=row.title,
        description=row.description,
    )


def to_module(row: ModuleRow) -> Module:
    return Module(
        id=row.id,
        slug=Slug(row.slug),
        status=ContentStatus(row.status),
        created_at=utc(row.created_at),
        updated_at=utc(row.updated_at),
        course_id=row.course_id,
        title=row.title,
        description=row.description,
        position=row.position,
    )


def to_section(row: SectionRow) -> Section:
    return Section(
        id=row.id,
        slug=Slug(row.slug),
        status=ContentStatus(row.status),
        created_at=utc(row.created_at),
        updated_at=utc(row.updated_at),
        module_id=row.module_id,
        title=row.title,
        description=row.description,
        position=row.position,
        content_type=SectionContentType(row.content_type),
        body=row.body,
    )
