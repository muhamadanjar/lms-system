"""Value objects that define immutable quiz-assessment semantics."""

from enum import StrEnum

from app.domain.exceptions import ValidationError


class AnswerPolicy(StrEnum):
    """Allowed cardinality for a multiple-choice question."""

    SINGLE = "SINGLE"
    MULTIPLE = "MULTIPLE"


class QuestionResultOutcome(StrEnum):
    """Learner-visible classification of a finalized snapshot question."""

    ANSWERED = "ANSWERED"
    WRONG = "WRONG"
    UNANSWERED = "UNANSWERED"


class QuestionCode(str):
    """Globally unique, canonical question identifier.

    Whitespace is intentionally accepted at the boundary and normalized here so
    a manual code cannot bypass uniqueness through casing or padding.
    """

    def __new__(cls, value: str) -> "QuestionCode":
        if not isinstance(value, str):
            raise ValidationError("question_code must be a string")
        normalized = value.strip().upper()
        if not normalized:
            raise ValidationError("question_code is required")
        if len(normalized) > 80:
            raise ValidationError("question_code exceeds 80 characters")
        if any(not (character.isalnum() or character in "-_") for character in normalized):
            raise ValidationError("question_code may contain only letters, numbers, '-' or '_'")
        return str.__new__(cls, normalized)
