"""course enrollment roster

Revision ID: 0009_course_enrollment
Revises: 0008_course_lab_access
"""
from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa


revision: str = "0009_course_enrollment"
down_revision: Union[str, None] = "0008_course_lab_access"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "enrollments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column("enrolled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], name="fk_enrollments_course_id_courses", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_enrollments_user_id", "enrollments", ["user_id"], unique=False)
    op.create_index("ix_enrollments_course_id", "enrollments", ["course_id"], unique=False)
    op.create_index("ix_enrollments_status", "enrollments", ["status"], unique=False)
    if op.get_bind().dialect.name == "postgresql" and not context.is_offline_mode():
        op.create_index(
            "uq_enrollments_user_course_live",
            "enrollments",
            ["user_id", "course_id"],
            unique=True,
            postgresql_where=sa.text("status = 'ENROLLED'"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_index("uq_enrollments_user_course_live", table_name="enrollments")
    op.drop_index("ix_enrollments_status", table_name="enrollments")
    op.drop_index("ix_enrollments_course_id", table_name="enrollments")
    op.drop_index("ix_enrollments_user_id", table_name="enrollments")
    op.drop_table("enrollments")
