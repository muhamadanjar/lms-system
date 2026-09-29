from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from app.domain.entities.enrollment import Enrollment


class EnrollmentRepository(ABC):
    """Port untuk episode kepesertaan per (user, course)."""

    @abstractmethod
    async def create(self, enrollment: Enrollment) -> Enrollment: ...

    @abstractmethod
    async def update(self, enrollment: Enrollment) -> Enrollment: ...

    @abstractmethod
    async def get_live(self, user_id: str, course_id: UUID) -> Optional[Enrollment]: ...

    @abstractmethod
    async def list_live_by_course(self, course_id: UUID) -> list[Enrollment]: ...

    @abstractmethod
    async def list_history(self, user_id: str, course_id: UUID) -> list[Enrollment]: ...
