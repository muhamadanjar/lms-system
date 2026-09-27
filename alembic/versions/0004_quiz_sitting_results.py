"""add immutable quiz sitting results and question codes

Revision ID: 0004_quiz_sitting_results
Revises: 0003_remote_server
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004_quiz_sitting_results"
down_revision: Union[str, None] = "0003_remote_server"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("quizzes", sa.Column("is_exam", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("quizzes", sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("quizzes", sa.Column("answer_policy", sa.String(length=12), nullable=False, server_default="SINGLE"))
    op.add_column("questions", sa.Column("question_code", sa.String(length=80), nullable=True))

    connection = op.get_bind()
    legacy_questions = connection.execute(sa.text("SELECT id FROM questions ORDER BY created_at, id")).all()
    for number, row in enumerate(legacy_questions, start=1):
        connection.execute(sa.text("UPDATE questions SET question_code = :code WHERE id = :id"), {"code": f"Q-{number:06d}", "id": row.id})
    op.alter_column("questions", "question_code", nullable=False)
    op.create_unique_constraint("uq_questions_question_code", "questions", ["question_code"])
    op.create_index("ix_questions_question_code", "questions", ["question_code"], unique=True)

    op.create_table(
        "question_code_sequences",
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("next_value", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("name", name="pk_question_code_sequences"),
    )
    connection.execute(sa.text("INSERT INTO question_code_sequences (name, next_value, updated_at) VALUES ('question_code', :next_value, CURRENT_TIMESTAMP)"), {"next_value": len(legacy_questions) + 1})

    op.add_column("quiz_sittings", sa.Column("active_sitting_key", sa.String(length=600), nullable=True))
    op.add_column("quiz_sittings", sa.Column("total_score", sa.Integer(), nullable=True))
    connection.execute(sa.text("UPDATE quiz_sittings SET active_sitting_key = CAST(quiz_id AS VARCHAR) || ':' || learner_id WHERE attempt_state = 'IN_PROGRESS'"))
    op.create_index("uq_quiz_sittings_active_key", "quiz_sittings", ["active_sitting_key"], unique=True)

    op.create_table(
        "quiz_sitting_questions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sitting_id", sa.Uuid(), nullable=False),
        sa.Column("source_question_id", sa.Uuid(), nullable=False),
        sa.Column("question_code", sa.String(length=80), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("question_type", sa.String(length=12), nullable=False),
        sa.Column("answer_policy", sa.String(length=12), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["sitting_id"], ["quiz_sittings.id"], name="fk_sitting_questions_sitting", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_question_id"], ["questions.id"], name="fk_sitting_questions_source_question"),
        sa.PrimaryKeyConstraint("id", name="pk_quiz_sitting_questions"),
        sa.UniqueConstraint("sitting_id", "question_code", name="uq_sitting_question_code"),
        sa.UniqueConstraint("sitting_id", "position", name="uq_sitting_question_position"),
    )
    op.create_index("ix_quiz_sitting_questions_sitting_id", "quiz_sitting_questions", ["sitting_id"])
    op.create_table(
        "quiz_sitting_options",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sitting_question_id", sa.Uuid(), nullable=False),
        sa.Column("source_answer_id", sa.Uuid(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["sitting_question_id"], ["quiz_sitting_questions.id"], name="fk_sitting_options_question", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_answer_id"], ["answers.id"], name="fk_sitting_options_source_answer"),
        sa.PrimaryKeyConstraint("id", name="pk_quiz_sitting_options"),
        sa.UniqueConstraint("sitting_question_id", "position", name="uq_sitting_option_position"),
    )
    op.create_index("ix_quiz_sitting_options_sitting_question_id", "quiz_sitting_options", ["sitting_question_id"])
    op.create_table(
        "quiz_sitting_answer_selections",
        sa.Column("sitting_question_id", sa.Uuid(), nullable=False),
        sa.Column("sitting_option_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["sitting_question_id"], ["quiz_sitting_questions.id"], name="fk_sitting_selections_question", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sitting_option_id"], ["quiz_sitting_options.id"], name="fk_sitting_selections_option", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("sitting_question_id", "sitting_option_id", name="pk_quiz_sitting_answer_selections"),
    )
    op.create_table(
        "quiz_sitting_question_results",
        sa.Column("sitting_question_id", sa.Uuid(), nullable=False),
        sa.Column("question_code", sa.String(length=80), nullable=False),
        sa.Column("outcome", sa.String(length=12), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["sitting_question_id"], ["quiz_sitting_questions.id"], name="fk_sitting_results_question", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("sitting_question_id", name="pk_quiz_sitting_question_results"),
    )
    op.create_table(
        "quiz_exam_attempt_counters",
        sa.Column("quiz_id", sa.Uuid(), nullable=False),
        sa.Column("learner_id", sa.String(length=255), nullable=False),
        sa.Column("finalized_attempts", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["quiz_id"], ["quizzes.id"], name="fk_exam_counter_quiz", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("quiz_id", "learner_id", name="pk_quiz_exam_attempt_counters"),
    )


def downgrade() -> None:
    op.drop_table("quiz_exam_attempt_counters")
    op.drop_table("quiz_sitting_question_results")
    op.drop_table("quiz_sitting_answer_selections")
    op.drop_index("ix_quiz_sitting_options_sitting_question_id", table_name="quiz_sitting_options")
    op.drop_table("quiz_sitting_options")
    op.drop_index("ix_quiz_sitting_questions_sitting_id", table_name="quiz_sitting_questions")
    op.drop_table("quiz_sitting_questions")
    op.drop_index("uq_quiz_sittings_active_key", table_name="quiz_sittings")
    op.drop_column("quiz_sittings", "total_score")
    op.drop_column("quiz_sittings", "active_sitting_key")
    op.drop_table("question_code_sequences")
    op.drop_index("ix_questions_question_code", table_name="questions")
    op.drop_constraint("uq_questions_question_code", "questions", type_="unique")
    op.drop_column("questions", "question_code")
    op.drop_column("quizzes", "answer_policy")
    op.drop_column("quizzes", "max_attempts")
    op.drop_column("quizzes", "is_exam")
