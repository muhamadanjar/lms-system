from app.domain.entities.answer import Answer
from app.domain.entities.question import Question
from app.domain.entities.quiz import Quiz
from app.domain.entities.quiz_sitting import QuizSitting
from app.domain.value_objects.content import ContentStatus, QuestionType, QuizAttemptState, Slug
from app.domain.value_objects.quiz_assessment import AnswerPolicy, QuestionCode
from app.infrastructure.persistence.mappers.content_mapper import utc
from app.infrastructure.persistence.models.answer import Answer as AnswerRow
from app.infrastructure.persistence.models.question import Question as QuestionRow
from app.infrastructure.persistence.models.quiz import Quiz as QuizRow
from app.infrastructure.persistence.models.quiz_sitting import QuizSitting as SittingRow


def to_quiz(row: QuizRow) -> Quiz:
    return Quiz(id=row.id, slug=Slug(row.slug), status=ContentStatus(row.status), created_at=utc(row.created_at), updated_at=utc(row.updated_at), section_id=row.section_id, is_exam=row.is_exam, max_attempts=row.max_attempts, answer_policy=AnswerPolicy(row.answer_policy))


def to_question(row: QuestionRow) -> Question:
    return Question(id=row.id, slug=Slug(row.slug), status=ContentStatus(row.status), created_at=utc(row.created_at), updated_at=utc(row.updated_at), quiz_id=row.quiz_id, prompt=row.prompt, question_type=QuestionType(row.question_type), weight=row.weight, position=row.position, question_code=QuestionCode(row.question_code))


def to_answer(row: AnswerRow, question_type: QuestionType) -> Answer:
    return Answer(id=row.id, slug=Slug(row.slug), status=ContentStatus(row.status), created_at=utc(row.created_at), updated_at=utc(row.updated_at), question_id=row.question_id, value=row.value, position=row.position, is_correct=row.is_correct, question_type=question_type)


def to_sitting(row: SittingRow) -> QuizSitting:
    return QuizSitting(id=row.id, slug=Slug(row.slug), status=ContentStatus(row.status), created_at=utc(row.created_at), updated_at=utc(row.updated_at), quiz_id=row.quiz_id, learner_id=row.learner_id, attempt_state=QuizAttemptState(row.attempt_state), started_at=utc(row.started_at), submitted_at=utc(row.submitted_at) if row.submitted_at else None, total_score=row.total_score)
