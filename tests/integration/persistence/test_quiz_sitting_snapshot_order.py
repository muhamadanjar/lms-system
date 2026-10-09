from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event, text
from sqlmodel import Session

from app.domain.entities.quiz_sitting_snapshot import (
    QuizSittingOptionSnapshot,
    QuizSittingQuestionSnapshot,
)
from app.domain.value_objects.content import QuestionType
from app.domain.value_objects.quiz_assessment import AnswerPolicy, QuestionCode
from app.infrastructure.persistence.repositories.quiz_sitting_repository import (
    SqlModelQuizSittingRepository,
)


class _AsyncSessionAdapter:
    def __init__(self, session: Session):
        self.session = session

    def add(self, instance) -> None:
        self.session.add(instance)

    async def flush(self) -> None:
        self.session.flush()


@pytest.mark.asyncio
async def test_save_snapshot_flushes_questions_before_options_with_foreign_keys():
    engine = create_engine("sqlite://")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record) -> None:
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE quiz_sittings (id CHAR(32) PRIMARY KEY)"
        )
        connection.exec_driver_sql(
            """CREATE TABLE quiz_sitting_questions (
                id CHAR(32) PRIMARY KEY,
                sitting_id CHAR(32) NOT NULL REFERENCES quiz_sittings(id),
                source_question_id CHAR(32) NOT NULL,
                question_code VARCHAR(80) NOT NULL,
                prompt TEXT NOT NULL,
                question_type VARCHAR(12) NOT NULL,
                answer_policy VARCHAR(12) NOT NULL,
                position INTEGER NOT NULL
            )"""
        )
        connection.exec_driver_sql(
            """CREATE TABLE quiz_sitting_options (
                id CHAR(32) PRIMARY KEY,
                sitting_question_id CHAR(32) NOT NULL
                    REFERENCES quiz_sitting_questions(id),
                source_answer_id CHAR(32) NOT NULL,
                value TEXT NOT NULL,
                position INTEGER NOT NULL,
                is_correct BOOLEAN NOT NULL
            )"""
        )

    sitting_id = uuid4()
    question_id = uuid4()
    option_id = uuid4()
    source_question_id = uuid4()
    source_answer_id = uuid4()
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO quiz_sittings (id) VALUES (?)", (sitting_id.hex,)
        )

    snapshot = QuizSittingQuestionSnapshot(
        id=question_id,
        sitting_id=sitting_id,
        source_question_id=source_question_id,
        question_code=QuestionCode("Q-000001"),
        prompt="Pick the answer",
        question_type=QuestionType.MULTICHOICE,
        answer_policy=AnswerPolicy.SINGLE,
        position=0,
        options=(
            QuizSittingOptionSnapshot(
                id=option_id,
                source_answer_id=source_answer_id,
                value="Option",
                position=0,
                is_correct=True,
            ),
        ),
    )

    session = Session(engine)
    try:
        repository = SqlModelQuizSittingRepository(
            session=_AsyncSessionAdapter(session), slugs=None
        )
        await repository.save_snapshot([snapshot])
        session.commit()
        assert session.exec(text("SELECT id FROM quiz_sitting_options")).first() is not None
    finally:
        session.close()
        engine.dispose()
