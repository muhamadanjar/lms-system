from typing import Optional
from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.entities.section import Section
from app.domain.exceptions import NotFoundError, ValidationError
from app.infrastructure.persistence.mappers.content_mapper import to_section
from app.infrastructure.persistence.models.module import Module as ModuleRow
from app.infrastructure.persistence.models.section import Section as SectionRow
from app.infrastructure.persistence.repositories.content_slug_repository import SqlModelContentSlugRegistry


class SqlModelSectionRepository:
    def __init__(self, session: AsyncSession, slugs: SqlModelContentSlugRegistry):
        self.session, self.slugs = session, slugs

    async def create(self, section: Section) -> Section:
        if await self.session.get(ModuleRow, section.module_id) is None:
            raise NotFoundError("module not found")
        await self.slugs.reserve(str(section.slug), section.id, "section")
        self.session.add(SectionRow(id=section.id, slug=str(section.slug), status=section.status, created_at=section.created_at, updated_at=section.updated_at, module_id=section.module_id, title=section.title, description=section.description, position=section.position, content_type=section.content_type, body=section.body))
        await self.session.flush()
        return section

    async def get_by_id(self, section_id: UUID) -> Optional[Section]:
        row = await self.session.get(SectionRow, section_id)
        return to_section(row) if row else None

    async def get_by_slug(self, module_id: UUID, slug: str) -> Optional[Section]:
        row = (await self.session.exec(select(SectionRow).where(SectionRow.module_id == module_id, SectionRow.slug == slug))).first()
        return to_section(row) if row else None

    async def get_hierarchy(self, section_id: UUID) -> Optional[Section]:
        return await self.get_by_id(section_id)

    async def list_by_module(self, module_id: UUID, include_archived: bool = False, offset: int = 0, limit: int = 20) -> list[Section]:
        query = select(SectionRow).where(SectionRow.module_id == module_id).order_by(SectionRow.position, SectionRow.id).offset(offset).limit(limit)
        if not include_archived:
            query = query.where(SectionRow.status != "ARCHIVED")
        return [to_section(row) for row in (await self.session.exec(query)).all()]

    async def count_by_module(self, module_id: UUID, include_archived: bool = False) -> int:
        from sqlalchemy import func
        query = select(func.count()).select_from(SectionRow).where(SectionRow.module_id == module_id)
        if not include_archived:
            query = query.where(SectionRow.status != "ARCHIVED")
        return int((await self.session.exec(query)).one())

    async def update(self, section: Section) -> Section:
        row = await self.session.get(SectionRow, section.id)
        if row is None:
            raise NotFoundError("section not found")
        if row.slug != str(section.slug) or row.module_id != section.module_id:
            raise ValidationError("section slug and parent are immutable in this operation")
        row.title, row.description, row.position, row.status, row.content_type, row.body, row.updated_at = section.title, section.description, section.position, section.status, section.content_type, section.body, section.updated_at
        await self.session.flush()
        return section

    async def reorder(self, module_id: UUID, ordered_ids: list[UUID]) -> None:
        rows = list((await self.session.exec(select(SectionRow).where(SectionRow.module_id == module_id))).all())
        if {row.id for row in rows} != set(ordered_ids):
            raise ValidationError("reorder must contain exactly the existing sections")
        by_id = {row.id: row for row in rows}
        for offset, row in enumerate(rows, start=1):
            row.position = -offset
        await self.session.flush()
        for position, section_id in enumerate(ordered_ids):
            by_id[section_id].position = position
        await self.session.flush()

    async def delete(self, section_id: UUID) -> bool:
        row = await self.session.get(SectionRow, section_id)
        if row is None:
            return False
        await self.slugs.release(str(row.slug), section_id)
        await self.session.delete(row)
        await self.session.flush()
        return True
