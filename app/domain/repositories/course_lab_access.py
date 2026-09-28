from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from app.domain.entities.course_lab_access import CourseLabAccess


class CourseLabAccessRepository(ABC):
    """Port untuk satu akses VPS per (user, course)."""

    @abstractmethod
    async def create(self, access: CourseLabAccess) -> CourseLabAccess: ...

    @abstractmethod
    async def update(self, access: CourseLabAccess) -> CourseLabAccess: ...

    @abstractmethod
    async def get_live(self, user_id: str, course_id: UUID) -> Optional[CourseLabAccess]: ...

    @abstractmethod
    async def list_live_by_course(self, course_id: UUID) -> list[CourseLabAccess]: ...

    @abstractmethod
    async def list_live_by_user(self, user_id: str) -> list[CourseLabAccess]: ...

    @abstractmethod
    async def find_active_by_server(self, server_id: UUID) -> Optional[CourseLabAccess]: ...

    @abstractmethod
    async def free_server_ids(self, limit: int) -> list[UUID]: ...
