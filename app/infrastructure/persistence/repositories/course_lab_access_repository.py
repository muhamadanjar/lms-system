from typing import Optional
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.entities.course_lab_access import CourseLabAccess, CourseLabAccessState
from app.domain.exceptions import ConflictError, NotFoundError
from app.domain.repositories.course_lab_access import CourseLabAccessRepository
from app.infrastructure.persistence.mappers.course_lab_access_mapper import to_course_lab_access
from app.infrastructure.persistence.models.course_lab_access import CourseLabAccess as AccessRow
from app.infrastructure.persistence.models.remote_server import RemoteServer


class SqlModelCourseLabAccessRepository(CourseLabAccessRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, access: CourseLabAccess) -> CourseLabAccess:
        self.session.add(
            AccessRow(
                id=access.id,
                user_id=access.user_id,
                course_id=access.course_id,
                server_id=access.server_id,
                state=access.state,
                created_at=access.created_at,
                updated_at=access.updated_at,
            )
        )
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise ConflictError("duplicate live course lab access") from exc
        return access

    async def update(self, access: CourseLabAccess) -> CourseLabAccess:
        row = await self.session.get(AccessRow, access.id)
        if row is None:
            raise NotFoundError("course lab access not found")
        if row.user_id != access.user_id or row.course_id != access.course_id:
            raise ValueError("lab access owner and course are immutable in this operation")
        row.server_id, row.state, row.updated_at = access.server_id, access.state, access.updated_at
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise ConflictError("duplicate live course lab access") from exc
        return access

    async def get_live(self, user_id: str, course_id: UUID) -> Optional[CourseLabAccess]:
        row = (
            await self.session.exec(
                select(AccessRow)
                .where(AccessRow.user_id == user_id)
                .where(AccessRow.course_id == course_id)
                .where(AccessRow.state == CourseLabAccessState.ACTIVE)
            )
        ).first()
        return to_course_lab_access(row) if row else None

    async def list_live_by_course(self, course_id: UUID) -> list[CourseLabAccess]:
        rows = list(
            (
                await self.session.exec(
                    select(AccessRow)
                    .where(AccessRow.course_id == course_id)
                    .where(AccessRow.state == CourseLabAccessState.ACTIVE)
                    .order_by(AccessRow.created_at)
                )
            ).all()
        )
        return [to_course_lab_access(row) for row in rows]

    async def list_live_by_user(self, user_id: str) -> list[CourseLabAccess]:
        rows = list(
            (
                await self.session.exec(
                    select(AccessRow)
                    .where(AccessRow.user_id == user_id)
                    .where(AccessRow.state == CourseLabAccessState.ACTIVE)
                    .order_by(AccessRow.created_at)
                )
            ).all()
        )
        return [to_course_lab_access(row) for row in rows]

    async def find_active_by_server(self, server_id: UUID) -> Optional[CourseLabAccess]:
        row = (
            await self.session.exec(
                select(AccessRow)
                .where(AccessRow.server_id == server_id)
                .where(AccessRow.state == CourseLabAccessState.ACTIVE)
            )
        ).first()
        return to_course_lab_access(row) if row else None

    async def free_server_ids(self, limit: int) -> list[UUID]:
        taken = select(AccessRow.server_id).where(AccessRow.state == CourseLabAccessState.ACTIVE)
        rows = list(
            (
                await self.session.exec(
                    select(RemoteServer.id)
                    .where(RemoteServer.deleted_at.is_(None))
                    .where(RemoteServer.id.not_in(taken))
                    .order_by(RemoteServer.created_at)
                    .limit(limit)
                )
            ).all()
        )
        return list(rows)
