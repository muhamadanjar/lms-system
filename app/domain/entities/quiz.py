from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from typing import Optional
from uuid import UUID

from app.domain.entities.base import ContentEntity
from app.domain.exceptions import ValidationError
from app.domain.value_objects.content import Slug
from app.domain.value_objects.quiz_assessment import AnswerPolicy

if TYPE_CHECKING:
    from app.domain.entities.question import Question


@dataclass
class KnowledgeQuiz(ContentEntity):
    course_id: UUID | None = None
    section_id: UUID | None = None
    title: str = "Quiz"
    description: Optional[str] = None
    is_exam: bool = False
    max_attempts: int = 1
    passing_score: int = 70
    answer_policy: AnswerPolicy = AnswerPolicy.SINGLE
    questions: list["Question"] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.course_id is None and self.section_id is None:
            raise ValidationError("course_id or section_id is required")
        if not self.title.strip():
            raise ValidationError("title is required")
        self.title = self.title.strip()
        if self.description is not None:
            self.description = self.description.strip()
        self.answer_policy = AnswerPolicy(self.answer_policy)
        if not isinstance(self.max_attempts, int) or self.max_attempts < 1:
            raise ValidationError("max_attempts must be a positive integer")
        self.set_passing_score(self.passing_score, touch=False)

    def set_passing_score(self, score: int, *, touch: bool = True) -> None:
        if not isinstance(score, int) or isinstance(score, bool) or not 0 <= score <= 100:
            raise ValidationError("passing_score must be an integer between 0 and 100")
        self.passing_score = score
        if touch:
            self.touch()

    def rename(self, title: str, description: str | None, slug: str | None = None) -> None:
        if not title.strip():
            raise ValidationError("title is required")
        self.title = title.strip()
        self.description = description.strip() if description is not None else None
        if slug is not None:
            requested = Slug(slug)
            if requested != self.slug:
                raise ValidationError("content slugs are immutable")
            self.slug = requested
        self.touch()

    def configure_assessment(self, *, is_exam: bool, max_attempts: int | None, answer_policy: AnswerPolicy, passing_score: int | None = None) -> None:
        """Set assessment policy; limits apply only when this is an exam."""
        if not isinstance(is_exam, bool):
            raise ValidationError("is_exam must be a boolean")
        resolved_max_attempts = 1 if is_exam and max_attempts is None else (max_attempts or self.max_attempts)
        if not isinstance(resolved_max_attempts, int) or resolved_max_attempts < 1:
            raise ValidationError("max_attempts must be a positive integer")
        self.is_exam = is_exam
        self.max_attempts = resolved_max_attempts
        self.answer_policy = AnswerPolicy(answer_policy)
        if passing_score is not None:
            self.set_passing_score(passing_score, touch=False)
        self.touch()


# Transitional name used by existing quiz assessment and learner APIs.
Quiz = KnowledgeQuiz
