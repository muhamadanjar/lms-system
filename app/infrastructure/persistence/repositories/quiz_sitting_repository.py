from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.entities.quiz_sitting import QuizSitting
from app.domain.exceptions import ConflictError, NotFoundError
from app.domain.value_objects.content import QuizAttemptState
from app.infrastructure.persistence.mappers.typed_content_mapper import to_sitting
from app.infrastructure.persistence.models.quiz import Quiz
from app.infrastructure.persistence.models.quiz_sitting import QuizSitting as SittingRow
from app.infrastructure.persistence.repositories.content_slug_repository import SqlModelContentSlugRegistry


class SqlModelQuizSittingRepository:
    def __init__(self, session: AsyncSession, slugs: SqlModelContentSlugRegistry):
        self.session, self.slugs = session, slugs

    async def create(self, sitting: QuizSitting) -> QuizSitting:
        if await self.session.get(Quiz, sitting.quiz_id) is None:
            raise NotFoundError("quiz not found")
        active = (await self.session.exec(select(SittingRow).where(SittingRow.quiz_id == sitting.quiz_id, SittingRow.learner_id == sitting.learner_id, SittingRow.attempt_state == QuizAttemptState.IN_PROGRESS))).first()
        if active:
            raise ConflictError("learner already has an active sitting for this quiz")
        await self.slugs.reserve(str(sitting.slug), sitting.id, "quiz_sitting")
        self.session.add(SittingRow(id=sitting.id, slug=str(sitting.slug), status=sitting.status, created_at=sitting.created_at, updated_at=sitting.updated_at, quiz_id=sitting.quiz_id, learner_id=sitting.learner_id, attempt_state=sitting.attempt_state, started_at=sitting.started_at, submitted_at=sitting.submitted_at))
        await self.session.flush()
        return sitting

    async def get_by_id(self, sitting_id: UUID) -> Optional[QuizSitting]:
        row = await self.session.get(SittingRow, sitting_id)
        return to_sitting(row) if row else None

    async def update(self, sitting: QuizSitting) -> QuizSitting:
        row = await self.session.get(SittingRow, sitting.id)
        if row is None:
            raise NotFoundError("quiz sitting not found")
        row.attempt_state, row.submitted_at, row.status, row.updated_at = sitting.attempt_state, sitting.submitted_at, sitting.status, sitting.updated_at
        await self.session.flush()
        return sitting
