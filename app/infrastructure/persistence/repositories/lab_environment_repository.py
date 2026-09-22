from typing import Optional
from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.entities.lab_environment import LabEnvironmentSettings
from app.domain.exceptions import ConflictError, NotFoundError, ValidationError
from app.domain.value_objects.content import SectionContentType
from app.infrastructure.persistence.mappers.typed_content_mapper import to_lab
from app.infrastructure.persistence.models.lab_environment_settings import LabEnvironmentSettings as LabRow
from app.infrastructure.persistence.models.section import Section
from app.infrastructure.persistence.repositories.content_slug_repository import SqlModelContentSlugRegistry


class SqlModelLabEnvironmentRepository:
    def __init__(self, session: AsyncSession, slugs: SqlModelContentSlugRegistry):
        self.session, self.slugs = session, slugs

    async def create(self, settings: LabEnvironmentSettings) -> LabEnvironmentSettings:
        section = await self.session.get(Section, settings.section_id)
        if section is None:
            raise NotFoundError("section not found")
        if section.content_type != SectionContentType.LAB_TASK:
            raise ValidationError("lab settings require a LAB_TASK section")
        existing = (await self.session.exec(select(LabRow).where(LabRow.section_id == settings.section_id))).first()
        if existing:
            raise ConflictError("section already has lab settings")
        await self.slugs.reserve(str(settings.slug), settings.id, "lab_environment_settings")
        self.session.add(LabRow(id=settings.id, slug=str(settings.slug), status=settings.status, created_at=settings.created_at, updated_at=settings.updated_at, section_id=settings.section_id, provider=settings.provider, region=settings.region, image=settings.image, cpu=settings.cpu, memory_mb=settings.memory_mb, storage_gb=settings.storage_gb, access_method=settings.access_method, username=settings.username, password_secret_ref=settings.password_secret_ref, public_key=settings.public_key, private_key_secret_ref=settings.private_key_secret_ref, network_policy=settings.network_policy, timeout_seconds=settings.timeout_seconds, cleanup_policy=settings.cleanup_policy))
        await self.session.flush()
        return settings

    async def get_by_section(self, section_id: UUID) -> Optional[LabEnvironmentSettings]:
        row = (await self.session.exec(select(LabRow).where(LabRow.section_id == section_id))).first()
        return to_lab(row) if row else None
