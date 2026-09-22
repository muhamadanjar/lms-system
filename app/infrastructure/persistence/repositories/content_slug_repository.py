from typing import Optional
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.exceptions import ConflictError, ValidationError
from app.infrastructure.persistence.models.content_slug_registry import ContentSlugRegistry


class SqlModelContentSlugRegistry:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def reserve(self, slug: str, content_id: UUID, content_kind: str) -> None:
        await self.assert_available(slug)
        self.session.add(ContentSlugRegistry(slug=slug, content_id=content_id, content_kind=content_kind))
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise ConflictError(f"slug is already reserved: {slug}") from exc

    async def assert_available(self, slug: str, excluding_content_id: Optional[UUID] = None) -> None:
        row = (await self.session.exec(select(ContentSlugRegistry).where(ContentSlugRegistry.slug == slug))).first()
        if row is not None and row.content_id != excluding_content_id:
            raise ConflictError(f"slug is already reserved: {slug}")

    async def release(self, slug: str, content_id: UUID) -> None:
        row = (await self.session.exec(select(ContentSlugRegistry).where(ContentSlugRegistry.slug == slug))).first()
        if row is not None:
            if row.content_id != content_id:
                raise ValidationError("slug registry ownership mismatch")
            await self.session.delete(row)
            await self.session.flush()

    async def release_ids(self, content_ids: list[UUID]) -> None:
        if not content_ids:
            return
        rows = list((await self.session.exec(select(ContentSlugRegistry).where(ContentSlugRegistry.content_id.in_(content_ids)))).all())
        for row in rows:
            await self.session.delete(row)
        await self.session.flush()
