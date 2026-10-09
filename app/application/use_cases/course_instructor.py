from collections.abc import Callable

from app.domain.entities.course_instructor import CourseInstructor
from app.domain.exceptions import NotFoundError


class CourseInstructorUseCases:
    """Assignment instructor ke course (admin-managed)."""

    def __init__(self, uow_factory: Callable):
        self.uow_factory = uow_factory

    async def assign(self, course_slug: str, user_id: str) -> CourseInstructor:
        async with self.uow_factory() as uow:
            course = await uow.courses.get_by_slug(course_slug)
            if course is None:
                raise NotFoundError("course not found")
            instructor = CourseInstructor(course_id=course.id, user_id=user_id)
            result = await uow.course_instructors.assign(instructor)
            await uow.commit()
            return result
