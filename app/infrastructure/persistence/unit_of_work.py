from collections.abc import Callable

from sqlmodel.ext.asyncio.session import AsyncSession

from app.application.ports.unit_of_work import UnitOfWorkPort
from app.config.config import get_settings
from app.infrastructure.crypto.aesgcm import AesGcmCredentialCipher, encode_credential_key
from app.infrastructure.persistence.repositories.content_slug_repository import SqlModelContentSlugRegistry
from app.infrastructure.persistence.repositories.course_lab_access_repository import SqlModelCourseLabAccessRepository
from app.infrastructure.persistence.repositories.course_repository import SqlModelCourseRepository
from app.infrastructure.persistence.repositories.enrollment_repository import SqlModelEnrollmentRepository
from app.infrastructure.persistence.repositories.module_repository import SqlModelModuleRepository
from app.infrastructure.persistence.repositories.quiz_repository import SqlModelQuizRepository
from app.infrastructure.persistence.repositories.quiz_sitting_repository import SqlModelQuizSittingRepository
from app.infrastructure.persistence.repositories.remote_server_repository import SqlModelRemoteServerRepository
from app.infrastructure.persistence.repositories.section_repository import SqlModelSectionRepository


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
        self.quizzes = SqlModelQuizRepository(self.session, self.slugs)
        self.sittings = SqlModelQuizSittingRepository(self.session, self.slugs)
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
