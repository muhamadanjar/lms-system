"""add preview visibility flag to sections

Revision ID: 0017_section_is_preview
Revises: 0016_section_terminal_enabled
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0017_section_is_preview"
down_revision: Union[str, None] = "0016_section_terminal_enabled"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sections",
        sa.Column("is_preview", sa.Boolean(), server_default=sa.false(), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("sections", "is_preview")
