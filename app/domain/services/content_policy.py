from app.domain.entities.answer import Answer
from app.domain.entities.question import Question
from app.domain.exceptions import ValidationError
from app.domain.value_objects.content import ContentStatus, QuestionType


def validate_publication(question: Question, answers: list[Answer]) -> None:
    if question.status is not ContentStatus.PUBLISHED:
        return
    if not answers:
        raise ValidationError("a published question requires at least one answer")
    if question.question_type is QuestionType.MULTICHOICE and not any(answer.is_correct for answer in answers):
        raise ValidationError("a published MULTICHOICE question requires a correct answer")


def validate_status_transition(current: ContentStatus, target: ContentStatus) -> None:
    allowed = {
        ContentStatus.DRAFT: {ContentStatus.DRAFT, ContentStatus.PUBLISHED, ContentStatus.ARCHIVED},
        ContentStatus.PUBLISHED: {ContentStatus.PUBLISHED, ContentStatus.ARCHIVED},
        ContentStatus.ARCHIVED: {ContentStatus.ARCHIVED},
    }
    if ContentStatus(target) not in allowed[ContentStatus(current)]:
        raise ValidationError(f"invalid content status transition: {current} -> {target}")
