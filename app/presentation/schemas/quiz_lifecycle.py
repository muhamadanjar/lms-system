from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.value_objects.content import ContentStatus
from app.domain.entities.quiz import KnowledgeQuiz
from app.domain.value_objects.quiz_assessment import AnswerPolicy


class QuizCreateRequest(BaseModel):
    slug: str = Field(min_length=1, max_length=160)
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    status: ContentStatus = ContentStatus.DRAFT


class QuizUpdateRequest(BaseModel):
    slug: str | None = Field(default=None, min_length=1, max_length=160)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    status: ContentStatus | None = None
    is_exam: bool | None = None
    max_attempts: int | None = Field(default=None, ge=1)
    answer_policy: AnswerPolicy | None = None
    passing_score: int | None = Field(default=None, ge=0, le=100)


class QuizSectionRead(BaseModel):
    module_slug: str
    module_title: str
    section_slug: str
    section_title: str


class QuizRead(BaseModel):
    id: UUID
    course_id: UUID
    section_id: UUID | None
    slug: str
    title: str
    description: str | None
    status: ContentStatus
    is_exam: bool
    max_attempts: int
    answer_policy: AnswerPolicy
    passing_score: int = 70
    section: QuizSectionRead | None
    created_at: datetime
    updated_at: datetime


class QuizLinkRequest(BaseModel):
    quiz_slug: str = Field(min_length=1, max_length=160)


def quiz_read(quiz: KnowledgeQuiz, section: dict[str, str] | None = None) -> QuizRead:
    return QuizRead(
        id=quiz.id, course_id=quiz.course_id, section_id=quiz.section_id, slug=str(quiz.slug),
        title=quiz.title, description=quiz.description, status=quiz.status,
        is_exam=quiz.is_exam, max_attempts=quiz.max_attempts, answer_policy=quiz.answer_policy, passing_score=quiz.passing_score,
        section=QuizSectionRead(**section) if section else None,
        created_at=quiz.created_at, updated_at=quiz.updated_at,
    )
