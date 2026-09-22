from enum import StrEnum
from typing import Any

from app.domain.exceptions import ValidationError


class ContentStatus(StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class SectionContentType(StrEnum):
    MATERIAL = "MATERIAL"
    LAB_TASK = "LAB_TASK"
    QUIZ = "QUIZ"


class QuestionType(StrEnum):
    MULTICHOICE = "MULTICHOICE"
    DIRECT = "DIRECT"


class AccessMethod(StrEnum):
    PASSWORD = "PASSWORD"
    PUBLIC_KEY = "PUBLIC_KEY"


class QuizAttemptState(StrEnum):
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    GRADED = "GRADED"
    CANCELLED = "CANCELLED"


class Slug(str):
    """Normalized, immutable public identifier."""

    def __new__(cls, value: str) -> "Slug":
        normalized = value.strip().lower()
        if not normalized or len(normalized) > 160:
            raise ValidationError("slug must contain 1-160 characters")
        if normalized != value or any(not (c.isalnum() or c in "-_") for c in normalized):
            raise ValidationError("slug must be lowercase and contain only letters, numbers, '-' or '_'")
        return str.__new__(cls, normalized)


def ensure_text(value: Any, field_name: str, max_length: int = 255) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field_name} is required")
    value = value.strip()
    if len(value) > max_length:
        raise ValidationError(f"{field_name} exceeds {max_length} characters")
    return value


def ensure_position(value: int) -> int:
    if not isinstance(value, int) or value < 0:
        raise ValidationError("position must be a non-negative integer")
    return value


def ensure_positive_weight(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError("weight must be a positive number") from exc
    if numeric <= 0:
        raise ValidationError("weight must be a positive number")
    return numeric
