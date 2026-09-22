"""Single import point for all SQLModel tables used by runtime and Alembic."""

from sqlmodel import SQLModel

from app.infrastructure.persistence.models.answer import Answer
from app.infrastructure.persistence.models.content_slug_registry import ContentSlugRegistry
from app.infrastructure.persistence.models.course import Course
from app.infrastructure.persistence.models.lab_environment_settings import LabEnvironmentSettings
from app.infrastructure.persistence.models.module import Module
from app.infrastructure.persistence.models.question import Question
from app.infrastructure.persistence.models.quiz import Quiz
from app.infrastructure.persistence.models.quiz_sitting import QuizSitting
from app.infrastructure.persistence.models.section import Section

__all__ = [
    "Answer",
    "ContentSlugRegistry",
    "Course",
    "LabEnvironmentSettings",
    "Module",
    "Question",
    "Quiz",
    "QuizSitting",
    "Section",
    "SQLModel",
]

metadata = SQLModel.metadata
