"""create lab and quiz content tables

Revision ID: 0002_typed_section_content
Revises: 0001_initial_content_hierarchy
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_typed_section_content"
down_revision: Union[str, None] = "0001_initial_content_hierarchy"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _common(name: str) -> list[sa.Column]:
    return [
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=9), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def _create_content_indexes(table: str) -> None:
    op.create_index(f"ix_{table}_slug", table, ["slug"], unique=False)


def upgrade() -> None:
    op.create_table(
        "lab_environment_settings",
        *_common("lab_environment_settings"),
        sa.Column("section_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("region", sa.String(length=100), nullable=True),
        sa.Column("image", sa.String(length=255), nullable=False),
        sa.Column("cpu", sa.Integer(), nullable=False),
        sa.Column("memory_mb", sa.Integer(), nullable=False),
        sa.Column("storage_gb", sa.Integer(), nullable=False),
        sa.Column("access_method", sa.String(length=10), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=False),
        sa.Column("password_secret_ref", sa.String(length=500), nullable=True),
        sa.Column("public_key", sa.Text(), nullable=True),
        sa.Column("private_key_secret_ref", sa.String(length=500), nullable=True),
        sa.Column("network_policy", sa.Text(), nullable=True),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("cleanup_policy", sa.String(length=80), nullable=False),
        sa.ForeignKeyConstraint(["section_id"], ["sections.id"], name="fk_lab_settings_section_id_sections", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_lab_environment_settings"),
        sa.UniqueConstraint("section_id", name="uq_lab_settings_section"),
    )
    _create_content_indexes("lab_environment_settings")
    op.create_index("ix_lab_environment_settings_section_id", "lab_environment_settings", ["section_id"], unique=False)

    op.create_table(
        "quizzes",
        *_common("quizzes"),
        sa.Column("section_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["section_id"], ["sections.id"], name="fk_quizzes_section_id_sections", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_quizzes"),
        sa.UniqueConstraint("section_id", name="uq_quizzes_section"),
    )
    _create_content_indexes("quizzes")
    op.create_index("ix_quizzes_section_id", "quizzes", ["section_id"], unique=False)

    op.create_table(
        "questions",
        *_common("questions"),
        sa.Column("quiz_id", sa.Uuid(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("question_type", sa.String(length=10), nullable=False),
        sa.Column("weight", sa.Numeric(12, 4), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["quiz_id"], ["quizzes.id"], name="fk_questions_quiz_id_quizzes", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_questions"),
        sa.UniqueConstraint("quiz_id", "position", name="uq_questions_quiz_position"),
    )
    _create_content_indexes("questions")
    op.create_index("ix_questions_quiz_id", "questions", ["quiz_id"], unique=False)

    op.create_table(
        "answers",
        *_common("answers"),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], name="fk_answers_question_id_questions", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_answers"),
        sa.UniqueConstraint("question_id", "position", name="uq_answers_question_position"),
    )
    _create_content_indexes("answers")
    op.create_index("ix_answers_question_id", "answers", ["question_id"], unique=False)

    op.create_table(
        "quiz_sittings",
        *_common("quiz_sittings"),
        sa.Column("quiz_id", sa.Uuid(), nullable=False),
        sa.Column("learner_id", sa.String(length=255), nullable=False),
        sa.Column("attempt_state", sa.String(length=12), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["quiz_id"], ["quizzes.id"], name="fk_quiz_sittings_quiz_id_quizzes", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_quiz_sittings"),
    )
    _create_content_indexes("quiz_sittings")
    op.create_index("ix_quiz_sittings_quiz_id", "quiz_sittings", ["quiz_id"], unique=False)
    op.create_index("ix_quiz_sittings_learner_id", "quiz_sittings", ["learner_id"], unique=False)
    op.create_index("ix_quiz_sittings_active_learner", "quiz_sittings", ["quiz_id", "learner_id", "attempt_state"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_quiz_sittings_active_learner", table_name="quiz_sittings")
    op.drop_index("ix_quiz_sittings_learner_id", table_name="quiz_sittings")
    op.drop_index("ix_quiz_sittings_quiz_id", table_name="quiz_sittings")
    op.drop_index("ix_quiz_sittings_slug", table_name="quiz_sittings")
    op.drop_table("quiz_sittings")
    op.drop_index("ix_answers_question_id", table_name="answers")
    op.drop_index("ix_answers_slug", table_name="answers")
    op.drop_table("answers")
    op.drop_index("ix_questions_quiz_id", table_name="questions")
    op.drop_index("ix_questions_slug", table_name="questions")
    op.drop_table("questions")
    op.drop_index("ix_quizzes_section_id", table_name="quizzes")
    op.drop_index("ix_quizzes_slug", table_name="quizzes")
    op.drop_table("quizzes")
    op.drop_index("ix_lab_environment_settings_section_id", table_name="lab_environment_settings")
    op.drop_index("ix_lab_environment_settings_slug", table_name="lab_environment_settings")
    op.drop_table("lab_environment_settings")
