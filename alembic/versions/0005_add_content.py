"""add content

Revision ID: 0005_add_content
Revises: 0004_quiz_sitting_results
Create Date: 2026-09-28 01:30:34.295928
"""
from typing import Sequence, Union

from alembic import op


revision: str = "0005_add_content"
down_revision: Union[str, None] = "0004_quiz_sitting_results"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enum values are validated in the domain and stored as VARCHAR.  Do not
    # introduce PostgreSQL enum types for these columns.
    op.drop_constraint(op.f('uq_remote_servers_name'), 'remote_servers', type_='unique')


def downgrade() -> None:
    op.create_unique_constraint(
        op.f("uq_remote_servers_name"),
        "remote_servers",
        ["name"],
        postgresql_nulls_not_distinct=False,
    )
