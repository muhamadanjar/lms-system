from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from app.application.ports.user_directory import DirectoryUnavailable, EmailAmbiguous, EmailNotFound, UserDirectory
from app.domain.entities.base import utc_now
from app.domain.entities.enrollment import Enrollment
from app.domain.exceptions import ConflictError, NotFoundError


class BulkEnrollResult:
    """Hasil per-item bulk enrollment."""

    def __init__(self):
        self.enrolled: list[Enrollment] = []
        self.skipped: list[dict] = []
        self.failed: list[dict] = []


class EnrollmentUseCases:
    """Episode kepesertaan learner per course."""

    def __init__(self, uow_factory: Callable, user_directory: UserDirectory | None = None):
        self.uow_factory = uow_factory
        self.user_directory = user_directory

    async def _get_course_id(self, uow, course_slug: str) -> UUID:
        course = await uow.courses.get_by_slug(course_slug)
        if course is None:
            raise NotFoundError("course not found")
        return course.id

    async def enroll(self, course_slug: str, user_id: str, enrolled_at: datetime | None = None) -> Enrollment:
        async with self.uow_factory() as uow:
            course_id = await self._get_course_id(uow, course_slug)
            existing = await uow.enrollments.get_live(user_id, course_id)
            if existing is not None:
                await uow.rollback()
                return existing
            enrollment = Enrollment(user_id=user_id, course_id=course_id, enrolled_at=enrolled_at or utc_now())
            try:
                result = await uow.enrollments.create(enrollment)
                await uow.commit()
                return result
            except ConflictError:
                await uow.rollback()
                retry = await uow.enrollments.get_live(user_id, course_id)
                if retry is None:
                    raise
                await uow.rollback()
                return retry

    @staticmethod
    def _entry_key(entry: dict) -> tuple[str, str] | None:
        user_id = (entry.get("user_id") or "").strip()
        if user_id:
            return ("id", user_id)
        email = (entry.get("email") or "").strip()
        if email:
            return ("email", email.lower())
        return None

    @staticmethod
    def _entry_identifier(entry: dict) -> str:
        user_id = (entry.get("user_id") or "").strip()
        if user_id:
            return user_id
        return (entry.get("email") or "").strip()

    async def _resolve_user_id(self, entry: dict, authorization: str | None) -> str | None:
        """Return canonical user_id, or None with failure recorded by caller.

        user_id wins when both are present (no lookup call).
        """
        user_id = (entry.get("user_id") or "").strip()
        if user_id:
            return user_id
        email = (entry.get("email") or "").strip()
        if self.user_directory is None:
            raise DirectoryUnavailable("user directory not configured")
        return await self.user_directory.find_user_id_by_email(email, authorization)

    async def bulk_enroll(self, course_slug: str, entries: list[dict], authorization: str | None = None) -> BulkEnrollResult:
        """Daftarkan banyak peserta dalam satu transaksi; gagal per item."""
        result = BulkEnrollResult()
        async with self.uow_factory() as uow:
            course_id = await self._get_course_id(uow, course_slug)
            seen: set[tuple[str, str]] = set()
            for entry in entries:
                key = self._entry_key(entry)
                identifier = self._entry_identifier(entry)
                if key is None:
                    result.failed.append({"identifier": identifier, "reason": "INVALID"})
                    continue
                if key in seen:
                    result.skipped.append({"identifier": identifier, "reason": "duplicate_in_request"})
                    continue
                seen.add(key)
                try:
                    user_id = await self._resolve_user_id(entry, authorization)
                except EmailNotFound:
                    result.failed.append({"identifier": identifier, "reason": "NOT_FOUND"})
                    continue
                except EmailAmbiguous:
                    result.failed.append({"identifier": identifier, "reason": "AMBIGUOUS"})
                    continue
                except DirectoryUnavailable:
                    result.failed.append({"identifier": identifier, "reason": "DIRECTORY_UNAVAILABLE"})
                    continue
                existing = await uow.enrollments.get_live(user_id, course_id)
                if existing is not None:
                    result.skipped.append({"identifier": identifier, "reason": "already_enrolled"})
                    continue
                try:
                    created = await uow.enrollments.create(Enrollment(user_id=user_id, course_id=course_id))
                except ConflictError:
                    retry = await uow.enrollments.get_live(user_id, course_id)
                    if retry is None:
                        result.failed.append({"identifier": identifier, "reason": "INVALID"})
                        continue
                    result.skipped.append({"identifier": identifier, "reason": "already_enrolled"})
                    continue
                result.enrolled.append(created)
            await uow.commit()
            return result

    async def my_enrollment(self, course_slug: str, user_id: str) -> Enrollment | None:
        async with self.uow_factory() as uow:
            course_id = await self._get_course_id(uow, course_slug)
            enrollment = await uow.enrollments.get_live(user_id, course_id)
            await uow.rollback()
            return enrollment

    async def list_course_enrollments(self, course_slug: str) -> list[Enrollment]:
        async with self.uow_factory() as uow:
            course_id = await self._get_course_id(uow, course_slug)
            live = await uow.enrollments.list_live_by_course(course_id)
            await uow.rollback()
            return live

    async def complete(self, course_slug: str, user_id: str, completed_at: datetime | None = None) -> Enrollment:
        async with self.uow_factory() as uow:
            course_id = await self._get_course_id(uow, course_slug)
            enrollment = await uow.enrollments.get_live(user_id, course_id)
            if enrollment is None:
                await uow.rollback()
                raise NotFoundError("enrollment not found")
            enrollment.complete(completed_at or utc_now())
            result = await uow.enrollments.update(enrollment)
            await uow.commit()
            return result

    async def withdraw(self, course_slug: str, user_id: str) -> Enrollment:
        async with self.uow_factory() as uow:
            course_id = await self._get_course_id(uow, course_slug)
            enrollment = await uow.enrollments.get_live(user_id, course_id)
            if enrollment is None:
                await uow.rollback()
                raise NotFoundError("enrollment not found")
            enrollment.withdraw()
            result = await uow.enrollments.update(enrollment)
            lab_repo = getattr(uow, "lab_access", None)
            if lab_repo is not None:
                access = await lab_repo.get_live(user_id, course_id)
                if access is not None:
                    access.release()
                    await lab_repo.update(access)
            await uow.commit()
            return result
