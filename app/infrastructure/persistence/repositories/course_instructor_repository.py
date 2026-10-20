from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.entities.course_instructor import CourseInstructor
from app.domain.exceptions import ConflictError
from app.domain.repositories.course_instructor import CourseInstructorRepository
from app.infrastructure.persistence.models.course_instructor import CourseInstructor as CourseInstructorRow


class SqlModelCourseInstructorRepository(CourseInstructorRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def assign(self, instructor: CourseInstructor) -> CourseInstructor:
        self.session.add(
            CourseInstructorRow(
                id=instructor.id,
                user_id=instructor.user_id,
                course_id=instructor.course_id,
                created_at=instructor.created_at,
                updated_at=instructor.updated_at,
            )
        )
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise ConflictError("instructor already assigned to course") from exc
        return instructor

    async def list_for_course(self, course_id):
        rows = (
            await self.session.exec(
                select(CourseInstructorRow)
                .where(CourseInstructorRow.course_id == course_id)
                .order_by(CourseInstructorRow.created_at, CourseInstructorRow.id)
            )
        ).all()
        return [_to_domain(row) for row in rows]

    async def list_for_user(self, user_id: str):
        rows = (
            await self.session.exec(
                select(CourseInstructorRow)
                .where(CourseInstructorRow.user_id == user_id)
                .order_by(CourseInstructorRow.course_id, CourseInstructorRow.created_at)
            )
        ).all()
        return [_to_domain(row) for row in rows]

    async def is_assigned(self, user_id: str, course_id) -> bool:
        row_id = (
            await self.session.exec(
                select(CourseInstructorRow.id)
                .where(CourseInstructorRow.user_id == user_id)
                .where(CourseInstructorRow.course_id == course_id)
            )
        ).first()
        return row_id is not None

    async def remove(self, course_id, user_id: str) -> bool:
        row = (
            await self.session.exec(
                select(CourseInstructorRow)
                .where(CourseInstructorRow.course_id == course_id)
                .where(CourseInstructorRow.user_id == user_id)
            )
        ).first()
        if row is None:
            return False
        await self.session.delete(row)
        await self.session.flush()
        return True


def _to_domain(row: CourseInstructorRow) -> CourseInstructor:
    return CourseInstructor(
        id=row.id,
        course_id=row.course_id,
        user_id=row.user_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
