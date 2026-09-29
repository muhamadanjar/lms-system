from collections.abc import Callable
from uuid import UUID

from app.domain.entities.course_lab_access import CourseLabAccess
from app.domain.exceptions import AuthorizationError, ConflictError, NotFoundError


class LabEnrollmentUseCases:
    """Satu akses VPS per (user, course)."""

    def __init__(self, uow_factory: Callable):
        self.uow_factory = uow_factory

    async def _get_course_id(self, uow, course_slug: str) -> UUID:
        course = await uow.courses.get_by_slug(course_slug)
        if course is None:
            raise NotFoundError("course not found")
        return course.id

    async def enroll(self, course_slug: str, user_id: str) -> CourseLabAccess:
        async with self.uow_factory() as uow:
            course_id = await self._get_course_id(uow, course_slug)
            enrollment = await uow.enrollments.get_live(user_id, course_id)
            if enrollment is None:
                await uow.rollback()
                raise AuthorizationError("ENROLLMENT_REQUIRED")
            existing = await uow.lab_access.get_live(user_id, course_id)
            if existing is not None:
                await uow.rollback()
                return existing
            for _ in range(3):
                free = await uow.lab_access.free_server_ids(1)
                if not free:
                    await uow.rollback()
                    raise ConflictError("CAPACITY_EXHAUSTED")
                try:
                    result = await uow.lab_access.create(
                        CourseLabAccess(user_id=user_id, course_id=course_id, server_id=free[0])
                    )
                    await uow.commit()
                    return result
                except ConflictError:
                    await uow.rollback()
                    retry = await uow.lab_access.get_live(user_id, course_id)
                    if retry is not None:
                        await uow.rollback()
                        return retry
            await uow.rollback()
            raise ConflictError("CAPACITY_EXHAUSTED")

    async def release(self, course_slug: str, user_id: str) -> CourseLabAccess:
        async with self.uow_factory() as uow:
            course_id = await self._get_course_id(uow, course_slug)
            access = await uow.lab_access.get_live(user_id, course_id)
            if access is None:
                await uow.rollback()
                raise NotFoundError("lab access not found")
            access.release()
            result = await uow.lab_access.update(access)
            await uow.commit()
            return result

    async def my_access(self, course_slug: str, user_id: str) -> CourseLabAccess | None:
        async with self.uow_factory() as uow:
            course_id = await self._get_course_id(uow, course_slug)
            access = await uow.lab_access.get_live(user_id, course_id)
            await uow.rollback()
            return access

    async def list_course_accesses(self, course_slug: str) -> list[CourseLabAccess]:
        async with self.uow_factory() as uow:
            course_id = await self._get_course_id(uow, course_slug)
            live = await uow.lab_access.list_live_by_course(course_id)
            await uow.rollback()
            return live

    async def user_has_course_server(self, user_id: str, server_id: UUID) -> bool:
        async with self.uow_factory() as uow:
            repo = getattr(uow, "lab_access", None)
            if repo is None:
                await uow.rollback()
                return False
            access = await repo.find_active_by_server(server_id)
            await uow.rollback()
            return access is not None and access.user_id == user_id
