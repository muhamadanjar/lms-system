"""Single import point for all SQLModel tables used by runtime and Alembic."""

from sqlmodel import SQLModel

from app.infrastructure.persistence.models.answer import Answer
from app.infrastructure.persistence.models.content_slug_registry import ContentSlugRegistry
from app.infrastructure.persistence.models.course import Course
from app.infrastructure.persistence.models.course_lab_access import CourseLabAccess
from app.infrastructure.persistence.models.enrollment import Enrollment
from app.infrastructure.persistence.models.module import Module
from app.infrastructure.persistence.models.question import Question
from app.infrastructure.persistence.models.quiz import Quiz
from app.infrastructure.persistence.models.quiz_sitting import QuizSitting
from app.infrastructure.persistence.models.question_code_sequence import QuestionCodeSequence
from app.infrastructure.persistence.models.quiz_exam_attempt_counter import QuizExamAttemptCounter
from app.infrastructure.persistence.models.quiz_sitting_answer_selection import QuizSittingAnswerSelection
from app.infrastructure.persistence.models.quiz_sitting_option import QuizSittingOption
from app.infrastructure.persistence.models.quiz_sitting_question import QuizSittingQuestion
from app.infrastructure.persistence.models.quiz_sitting_question_result import QuizSittingQuestionResult
from app.infrastructure.persistence.models.remote_server import RemoteServer
from app.infrastructure.persistence.models.section import Section

__all__ = [
    "Answer",
    "ContentSlugRegistry",
    "Course",
    "CourseLabAccess",
    "Enrollment",
    "Module",
    "Question",
    "QuestionCodeSequence",
    "Quiz",
    "QuizExamAttemptCounter",
    "QuizSitting",
    "QuizSittingAnswerSelection",
    "QuizSittingOption",
    "QuizSittingQuestion",
    "QuizSittingQuestionResult",
    "RemoteServer",
    "Section",
    "SQLModel",
]

metadata = SQLModel.metadata
