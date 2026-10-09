from abc import ABC, abstractmethod

from app.domain.entities.course_instructor import CourseInstructor


class CourseInstructorRepository(ABC):
    """Port untuk assignment instructor per (course, user)."""

    @abstractmethod
    async def assign(self, instructor: CourseInstructor) -> CourseInstructor: ...
