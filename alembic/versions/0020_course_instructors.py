"""course instructors join table

Revision ID: 0020_course_instructors
Revises: 0019_collect_task_file_staging
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0020_course_instructors"
down_revision: Union[str, None] = "0019_collect_task_file_staging"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        "course_instructors",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], name="fk_course_instructors_course_id_courses", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("course_id", "user_id", name="uq_course_instructors_course_user"),
    )
    op.create_index("ix_course_instructors_user_id", "course_instructors", ["user_id"], unique=False)
    op.create_index("ix_course_instructors_course_id", "course_instructors", ["course_id"], unique=False)

def downgrade() -> None:
    op.drop_index("ix_course_instructors_course_id", table_name="course_instructors")
    op.drop_index("ix_course_instructors_user_id", table_name="course_instructors")
    op.drop_table("course_instructors")
