from sqlalchemy.exc import IntegrityError
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
