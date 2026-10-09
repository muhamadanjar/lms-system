from collections.abc import Callable
from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.application.ports.unit_of_work import UnitOfWorkPort
from app.config.config import get_settings
from app.domain.entities.enrollment import EnrollmentStatus
from app.infrastructure.crypto.aesgcm import AesGcmCredentialCipher, encode_credential_key
from app.infrastructure.persistence.models.enrollment import Enrollment as EnrollmentRow
from app.infrastructure.persistence.repositories.content_slug_repository import SqlModelContentSlugRegistry
from app.infrastructure.persistence.repositories.course_instructor_repository import SqlModelCourseInstructorRepository
from app.infrastructure.persistence.repositories.course_lab_access_repository import SqlModelCourseLabAccessRepository
from app.infrastructure.persistence.repositories.course_repository import SqlModelCourseRepository
from app.infrastructure.persistence.repositories.enrollment_repository import SqlModelEnrollmentRepository
from app.infrastructure.persistence.repositories.module_repository import SqlModelModuleRepository
from app.infrastructure.persistence.repositories.quiz_repository import SqlModelQuizRepository
from app.infrastructure.persistence.repositories.quiz_sitting_repository import SqlModelQuizSittingRepository
from app.infrastructure.persistence.repositories.remote_server_repository import SqlModelRemoteServerRepository
from app.infrastructure.persistence.repositories.section_repository import SqlModelSectionRepository
from app.infrastructure.persistence.repositories.learning_progress_repository import SqlModelLearningProgressRepository
from app.infrastructure.persistence.repositories.lms_overview_repository import SqlModelLmsOverviewRepository


def default_credential_cipher() -> AesGcmCredentialCipher:
    settings = get_settings().ssh
    return AesGcmCredentialCipher(encode_credential_key(settings.credential_enc_key), settings.credential_key_version)


class SqlModelUnitOfWork(UnitOfWorkPort):
    def __init__(self, session_factory: Callable[[], AsyncSession] | None = None, session: AsyncSession | None = None):
        self.session_factory = session_factory
        self.session = session
        self._owned_session = False
        self._committed = False

    async def __aenter__(self):
        self._committed = False
        if self.session is None:
            if self.session_factory is None:
                raise ValueError("session or session_factory is required")
            self.session = self.session_factory()
            self._owned_session = True
        self.slugs = SqlModelContentSlugRegistry(self.session)
        self.courses = SqlModelCourseRepository(self.session, self.slugs)
        self.modules = SqlModelModuleRepository(self.session, self.slugs)
        self.sections = SqlModelSectionRepository(self.session, self.slugs)
        self.lab_access = SqlModelCourseLabAccessRepository(self.session)
        self.enrollments = SqlModelEnrollmentRepository(self.session)
        self.course_instructors = SqlModelCourseInstructorRepository(self.session)
        self.quizzes = SqlModelQuizRepository(self.session, self.slugs)
        self.sittings = SqlModelQuizSittingRepository(self.session, self.slugs)
        self.learning_progress = SqlModelLearningProgressRepository(self.session)
        self.overviews = SqlModelLmsOverviewRepository(self.session)
        self.servers = SqlModelRemoteServerRepository(self.session, default_credential_cipher)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if exc_type is not None or not self._committed:
            await self.rollback()
        if self._owned_session and self.session is not None:
            await self.session.close()

    async def commit(self) -> None:
        assert self.session is not None
        await self.session.commit()
        self._committed = True

    async def rollback(self) -> None:
        if self.session is not None:
            await self.session.rollback()

    async def lock_collect_task_submission(self, learner_id: str, course_id: UUID) -> None:
        """Lock the active enrollment row to serialize this learner's task submissions."""
        assert self.session is not None
        await self.session.exec(
            select(EnrollmentRow.id)
            .where(EnrollmentRow.user_id == learner_id)
            .where(EnrollmentRow.course_id == course_id)
            .where(EnrollmentRow.status == EnrollmentStatus.ENROLLED)
            .with_for_update()
        )
