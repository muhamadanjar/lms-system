"""Regression: snapshot question rows must be inserted before their options.

`QuizSittingQuestion`/`QuizSittingOption` carry no ORM relationship, so the unit
of work does not order their inserts. On Postgres (FK enforced) an unordered
flush raises ForeignKeyViolation and surfaces to clients as 409 RESOURCE_CONFLICT.
"""

from sqlalchemy import event

from app.domain.entities.quiz_sitting_snapshot import (
    QuizSittingOptionSnapshot,
    QuizSittingQuestionSnapshot,
)
from app.domain.value_objects.content import QuestionType
from app.domain.value_objects.quiz_assessment import AnswerPolicy, QuestionCode
from app.infrastructure.persistence.repositories.quiz_sitting_repository import (
    SqlModelQuizSittingRepository,
)

async def test_snapshot_inserts_questions_before_options(session):
    statements: list[str] = []

    def record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    engine = session._session.bind
    event.listen(engine, "before_cursor_execute", record)
    try:
        snapshot = QuizSittingQuestionSnapshot(
            question_code=QuestionCode("Q-000001"),
            prompt="Correct?",
            question_type=QuestionType.MULTICHOICE,
            answer_policy=AnswerPolicy.SINGLE,
            options=(
                QuizSittingOptionSnapshot(value="Yes", position=0, is_correct=True),
                QuizSittingOptionSnapshot(value="No", position=1, is_correct=False),
            ),
        )
        repository = SqlModelQuizSittingRepository(session, slugs=None)
        await repository.save_snapshot([snapshot])
        await session.flush()
    finally:
        event.remove(engine, "before_cursor_execute", record)

    def first_insert(table: str) -> int:
        return next(
            index
            for index, statement in enumerate(statements)
            if statement.lstrip().upper().startswith("INSERT") and table in statement
        )

    assert first_insert("quiz_sitting_questions") < first_insert("quiz_sitting_options")
