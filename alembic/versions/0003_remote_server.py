"""create remote server console tables

Revision ID: 0003_remote_server
Revises: 0002_typed_section_content
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_remote_server"
down_revision: Union[str, None] = "0002_typed_section_content"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "remote_servers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("host", sa.String(length=255), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=False),
        sa.Column("access_method", sa.String(length=11), nullable=False),
        sa.Column("credential_ciphertext", sa.Text(), nullable=True),
        sa.Column("credential_nonce", sa.Text(), nullable=True),
        sa.Column("credential_key_version", sa.Integer(), nullable=True),
        sa.Column("host_key", sa.Text(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_remote_servers"),
        sa.UniqueConstraint("name", name="uq_remote_servers_name"),
    )
    op.create_index("ix_remote_servers_name", "remote_servers", ["name"], unique=True)
    op.create_index("ix_remote_servers_deleted_at", "remote_servers", ["deleted_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_remote_servers_deleted_at", table_name="remote_servers")
    op.drop_index("ix_remote_servers_name", table_name="remote_servers")
    op.drop_table("remote_servers")