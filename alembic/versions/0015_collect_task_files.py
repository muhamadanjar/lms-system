"""private task evidence files and immutable submission associations

Revision ID: 0015_collect_task_files
Revises: 0014_course_progress_tasks
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0015_collect_task_files"
down_revision: Union[str, None] = "0014_course_progress_tasks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "files",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_backend", sa.String(length=16), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("uploaded_by", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_backend", "storage_key", name="uq_files_backend_storage_key"),
        sa.CheckConstraint("size_bytes > 0", name="ck_files_size_positive"),
        sa.CheckConstraint("storage_backend IN ('local','s3')", name="ck_files_storage_backend"),
    )
    op.create_index("ix_files_uploaded_by", "files", ["uploaded_by"])
    op.create_table(
        "collect_task_files",
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("file_id", sa.Uuid(), nullable=False),
        sa.Column("history_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["collect_tasks.id"], ondelete="CASCADE", name="fk_collect_task_files_task_id_collect_tasks"),
        sa.ForeignKeyConstraint(["file_id"], ["files.id"], ondelete="CASCADE", name="fk_collect_task_files_file_id_files"),
        sa.ForeignKeyConstraint(["history_id"], ["collect_task_history.id"], ondelete="CASCADE", name="fk_collect_task_files_history_id_collect_task_history"),
        sa.PrimaryKeyConstraint("task_id", "file_id", "history_id"),
        sa.UniqueConstraint("history_id", "file_id", name="uq_collect_task_files_history_file"),
    )
    op.create_index("ix_collect_task_files_task_history", "collect_task_files", ["task_id", "history_id"])


def downgrade() -> None:
    op.drop_index("ix_collect_task_files_task_history", table_name="collect_task_files")
    op.drop_table("collect_task_files")
    op.drop_index("ix_files_uploaded_by", table_name="files")
    op.drop_table("files")
