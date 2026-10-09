"""course progression policies and collected lab tasks

Revision ID: 0014_course_progress_tasks
Revises: 0013_question_type_length
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0014_course_progress_tasks"
down_revision: Union[str, None] = "0013_question_type_length"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("courses", sa.Column("progression_mode", sa.String(length=12), nullable=False, server_default="FREE"))
    op.add_column("courses", sa.Column("completion_mode", sa.String(length=16), nullable=False, server_default="ADMIN_REVIEW"))
    op.create_check_constraint("ck_courses_progression_mode", "courses", "progression_mode IN ('FREE','SEQUENTIAL')")
    op.create_check_constraint("ck_courses_completion_mode", "courses", "completion_mode IN ('SELF_LEARNING','ADMIN_REVIEW')")
    op.alter_column("courses", "completion_mode", existing_type=sa.String(length=16), existing_nullable=False, server_default="SELF_LEARNING")
    op.add_column("sections", sa.Column("requires_pass", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("quizzes", sa.Column("passing_score", sa.Integer(), nullable=False, server_default="70"))
    op.create_check_constraint("ck_quizzes_passing_score_range", "quizzes", "passing_score >= 0 AND passing_score <= 100")

    op.create_table(
        "section_completions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("learner_id", sa.String(length=255), nullable=False),
        sa.Column("section_id", sa.Uuid(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["section_id"], ["sections.id"], ondelete="CASCADE", name="fk_section_completions_section_id_sections"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("learner_id", "section_id", name="uq_section_completions_learner_section"),
    )
    op.create_index("ix_section_completions_learner_id", "section_completions", ["learner_id"])
    op.create_index("ix_section_completions_section_id", "section_completions", ["section_id"])
    op.create_table(
        "collect_tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("learner_id", sa.String(length=255), nullable=False),
        sa.Column("section_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["section_id"], ["sections.id"], ondelete="CASCADE", name="fk_collect_tasks_section_id_sections"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("learner_id", "section_id", name="uq_collect_tasks_learner_section"),
        sa.CheckConstraint("status IN ('SUBMITTED','IN_REVIEW','REVISION_REQUIRED','REVIEWED','PASSED')", name="ck_collect_tasks_status"),
        sa.CheckConstraint("score IS NULL OR (score >= 0 AND score <= 100)", name="ck_collect_tasks_score_range"),
    )
    op.create_index("ix_collect_tasks_section_status", "collect_tasks", ["section_id", "status"])
    op.create_index("ix_collect_tasks_learner_id", "collect_tasks", ["learner_id"])
    op.create_index("ix_collect_tasks_section_id", "collect_tasks", ["section_id"])
    op.create_table(
        "collect_task_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.String(length=255), nullable=False),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("submission_text", sa.Text(), nullable=True),
        sa.Column("evidence_urls", sa.JSON(), nullable=True),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["collect_tasks.id"], ondelete="CASCADE", name="fk_collect_task_history_task_id_collect_tasks"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("score IS NULL OR (score >= 0 AND score <= 100)", name="ck_collect_task_history_score_range"),
    )
    op.create_index("ix_collect_task_history_task_id", "collect_task_history", ["task_id"])


def downgrade() -> None:
    op.drop_index("ix_collect_task_history_task_id", table_name="collect_task_history")
    op.drop_table("collect_task_history")
    op.drop_index("ix_collect_tasks_section_status", table_name="collect_tasks")
    op.drop_index("ix_collect_tasks_learner_id", table_name="collect_tasks")
    op.drop_index("ix_collect_tasks_section_id", table_name="collect_tasks")
    op.drop_table("collect_tasks")
    op.drop_index("ix_section_completions_learner_id", table_name="section_completions")
    op.drop_index("ix_section_completions_section_id", table_name="section_completions")
    op.drop_table("section_completions")
    op.drop_constraint("ck_quizzes_passing_score_range", "quizzes", type_="check")
    op.drop_column("quizzes", "passing_score")
    op.drop_column("sections", "requires_pass")
    op.drop_constraint("ck_courses_completion_mode", "courses", type_="check")
    op.drop_constraint("ck_courses_progression_mode", "courses", type_="check")
    op.drop_column("courses", "completion_mode")
    op.drop_column("courses", "progression_mode")
