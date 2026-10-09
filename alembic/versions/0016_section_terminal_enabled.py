"""add optional learner terminal flag to lab task sections

Revision ID: 0016_section_terminal_enabled
Revises: 0015_collect_task_files
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0016_section_terminal_enabled"
down_revision: Union[str, None] = "0015_collect_task_files"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sections",
        sa.Column(
            "terminal_enabled",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("sections", "terminal_enabled")
