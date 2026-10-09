"""stage learner CollectTask files in their own transaction

Revision ID: 0019_collect_task_file_staging
Revises: 0018_course_watch_position
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0019_collect_task_file_staging"
down_revision: Union[str, None] = "0018_course_watch_position"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    with op.batch_alter_table("files") as batch_op:
        batch_op.add_column(sa.Column("upload_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(
        "ix_files_staged_upload_expiration",
        "files",
        ["upload_expires_at"],
    )
    with op.batch_alter_table("collect_task_files") as batch_op:
        batch_op.create_unique_constraint("uq_collect_task_files_file_id", ["file_id"])


def downgrade() -> None:
    with op.batch_alter_table("collect_task_files") as batch_op:
        batch_op.drop_constraint("uq_collect_task_files_file_id", type_="unique")
    op.drop_index("ix_files_staged_upload_expiration", table_name="files")
    with op.batch_alter_table("files") as batch_op:
        batch_op.drop_column("upload_expires_at")
