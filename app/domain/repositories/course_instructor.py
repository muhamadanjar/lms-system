from abc import ABC, abstractmethod

from app.domain.entities.course_instructor import CourseInstructor


class CourseInstructorRepository(ABC):
    """Port untuk assignment instructor per (course, user)."""

    @abstractmethod
    async def assign(self, instructor: CourseInstructor) -> CourseInstructor: ...

    async def list_for_course(self, course_id):
        raise NotImplementedError

    async def list_for_user(self, user_id: str):
        raise NotImplementedError

    async def is_assigned(self, user_id: str, course_id):
        raise NotImplementedError

    async def remove(self, course_id, user_id: str):
        raise NotImplementedError
