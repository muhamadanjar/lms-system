from typing import Optional
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.entities.enrollment import Enrollment, EnrollmentStatus
from app.domain.exceptions import ConflictError, NotFoundError
from app.domain.repositories.enrollment import EnrollmentRepository
from app.infrastructure.persistence.mappers.enrollment_mapper import to_enrollment
from app.infrastructure.persistence.models.enrollment import Enrollment as EnrollmentRow


class SqlModelEnrollmentRepository(EnrollmentRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, enrollment: Enrollment) -> Enrollment:
        self.session.add(
            EnrollmentRow(
                id=enrollment.id,
                user_id=enrollment.user_id,
                course_id=enrollment.course_id,
                status=enrollment.status,
                enrolled_at=enrollment.enrolled_at,
                completed_at=enrollment.completed_at,
                created_at=enrollment.created_at,
                updated_at=enrollment.updated_at,
            )
        )
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise ConflictError("duplicate live enrollment") from exc
        return enrollment

    async def update(self, enrollment: Enrollment) -> Enrollment:
        row = await self.session.get(EnrollmentRow, enrollment.id)
        if row is None:
            raise NotFoundError("enrollment not found")
        if row.user_id != enrollment.user_id or row.course_id != enrollment.course_id:
            raise ValueError("enrollment owner and course are immutable in this operation")
        row.status, row.completed_at, row.updated_at = enrollment.status, enrollment.completed_at, enrollment.updated_at
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise ConflictError("duplicate live enrollment") from exc
        return enrollment

    async def get_live(self, user_id: str, course_id: UUID) -> Optional[Enrollment]:
        row = (
            await self.session.exec(
                select(EnrollmentRow)
                .where(EnrollmentRow.user_id == user_id)
                .where(EnrollmentRow.course_id == course_id)
                .where(EnrollmentRow.status == EnrollmentStatus.ENROLLED)
            )
        ).first()
        return to_enrollment(row) if row else None

    async def list_live_by_course(self, course_id: UUID) -> list[Enrollment]:
        rows = list(
            (
                await self.session.exec(
                    select(EnrollmentRow)
                    .where(EnrollmentRow.course_id == course_id)
                    .where(EnrollmentRow.status == EnrollmentStatus.ENROLLED)
                    .order_by(EnrollmentRow.enrolled_at)
                )
            ).all()
        )
        return [to_enrollment(row) for row in rows]

    async def list_history(self, user_id: str, course_id: UUID) -> list[Enrollment]:
        rows = list(
            (
                await self.session.exec(
                    select(EnrollmentRow)
                    .where(EnrollmentRow.user_id == user_id)
                    .where(EnrollmentRow.course_id == course_id)
                    .order_by(EnrollmentRow.created_at.desc())
                )
            ).all()
        )
        return [to_enrollment(row) for row in rows]
