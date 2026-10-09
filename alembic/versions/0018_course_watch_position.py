"""persist the last opened section for each course enrollment

Revision ID: 0018_course_watch_position
Revises: 0017_section_is_preview
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0018_course_watch_position"
down_revision: Union[str, None] = "0017_section_is_preview"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    # batch mode: SQLite cannot ALTER-add a foreign key; Postgres uses plain ALTERs
    with op.batch_alter_table("enrollments") as batch_op:
        batch_op.add_column(
            sa.Column("last_opened_section_id", sa.Uuid(), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_enrollments_last_opened_section_id_sections",
            "sections",
            ["last_opened_section_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("enrollments") as batch_op:
        batch_op.drop_constraint(
            "fk_enrollments_last_opened_section_id_sections", type_="foreignkey"
        )
        batch_op.drop_column("last_opened_section_id")
