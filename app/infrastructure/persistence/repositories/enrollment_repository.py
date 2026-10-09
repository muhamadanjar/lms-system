from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import String, cast, func, or_
from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.entities.enrollment import Enrollment, EnrollmentStatus
from app.domain.exceptions import ConflictError, NotFoundError
from app.domain.repositories.enrollment import EnrollmentRepository
from app.infrastructure.persistence.mappers.enrollment_mapper import to_enrollment
from app.infrastructure.persistence.models.enrollment import Enrollment as EnrollmentRow
from app.infrastructure.persistence.models.course import Course as CourseRow


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
                last_opened_section_id=enrollment.last_opened_section_id,
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
        row.last_opened_section_id = enrollment.last_opened_section_id
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

    async def list_admin(
        self,
        *,
        search: str | None,
        course_slug: str | None,
        enrolled_from: datetime | None,
        enrolled_to: datetime | None,
        status: str | None,
        offset: int,
        limit: int,
    ) -> tuple[list[tuple[Enrollment, str, str]], int]:
        query = select(EnrollmentRow, CourseRow.slug, CourseRow.title).join(
            CourseRow, CourseRow.id == EnrollmentRow.course_id
        )
        count_query = select(func.count()).select_from(EnrollmentRow).join(
            CourseRow, CourseRow.id == EnrollmentRow.course_id
        )
        filters = []
        if course_slug is not None:
            filters.append(CourseRow.slug == course_slug)
        if enrolled_from is not None:
            filters.append(EnrollmentRow.enrolled_at >= enrolled_from)
        if enrolled_to is not None:
            filters.append(EnrollmentRow.enrolled_at <= enrolled_to)
        if status is not None:
            filters.append(EnrollmentRow.status == status)
        if search:
            pattern = f"%{search.strip()}%"
            filters.append(or_(
                EnrollmentRow.user_id.ilike(pattern),
                cast(EnrollmentRow.id, String).ilike(pattern),
                CourseRow.title.ilike(pattern),
                CourseRow.slug.ilike(pattern),
                EnrollmentRow.status.ilike(pattern),
            ))
        if filters:
            query = query.where(*filters)
            count_query = count_query.where(*filters)
        total = int((await self.session.exec(count_query)).one())
        rows = (await self.session.exec(
            query.order_by(EnrollmentRow.enrolled_at.desc(), EnrollmentRow.id)
            .offset(offset)
            .limit(limit)
        )).all()
        return [(to_enrollment(row), slug, title) for row, slug, title in rows], total

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

    async def list_history_by_user(self, user_id: str) -> list[Enrollment]:
        rows = list(
            (
                await self.session.exec(
                    select(EnrollmentRow)
                    .where(EnrollmentRow.user_id == user_id)
                    .order_by(EnrollmentRow.created_at.desc(), EnrollmentRow.id)
                )
            ).all()
        )
        return [to_enrollment(row) for row in rows]
