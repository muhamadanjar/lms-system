from app.domain.entities.answer import Answer
from app.domain.entities.question import Question
from app.domain.exceptions import ValidationError
from app.domain.value_objects.content import ContentStatus, QuestionType
from app.domain.value_objects.quiz_assessment import AnswerPolicy


def validate_publication(question: Question, answers: list[Answer]) -> None:
    if question.status is not ContentStatus.PUBLISHED:
        return
    if not answers:
        raise ValidationError("a published question requires at least one answer")
    if question.question_type is QuestionType.MULTICHOICE and not any(answer.is_correct for answer in answers):
        raise ValidationError("a published MULTICHOICE question requires a correct answer")


def validate_question_ready_for_attempt(question: Question, answers: list[Answer], policy: AnswerPolicy) -> None:
    """Reject incomplete MULTICHOICE drafts before a new sitting is snapshotted."""
    if not question.prompt.strip():
        raise ValidationError("every question requires a prompt before an attempt")
    if len(answers) < 2:
        raise ValidationError("every question requires at least two options before an attempt")
    correct_count = sum(answer.is_correct is True for answer in answers)
    if policy is AnswerPolicy.SINGLE and correct_count != 1:
        raise ValidationError("SINGLE quizzes require exactly one correct option per question")
    if policy is AnswerPolicy.MULTIPLE and correct_count < 1:
        raise ValidationError("MULTIPLE quizzes require at least one correct option per question")


def validate_status_transition(current: ContentStatus, target: ContentStatus) -> None:
    allowed = {
        ContentStatus.DRAFT: {ContentStatus.DRAFT, ContentStatus.PUBLISHED, ContentStatus.ARCHIVED},
        ContentStatus.PUBLISHED: {ContentStatus.PUBLISHED, ContentStatus.ARCHIVED},
        ContentStatus.ARCHIVED: {ContentStatus.ARCHIVED},
    }
    if ContentStatus(target) not in allowed[ContentStatus(current)]:
        raise ValidationError(f"invalid content status transition: {current} -> {target}")
