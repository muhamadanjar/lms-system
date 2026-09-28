"""per-user lab server assignments

Revision ID: 0007_lab_assignments
Revises: 0006_store_enums_as_strings
"""
from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa


revision: str = "0007_lab_assignments"
down_revision: Union[str, None] = "0006_store_enums_as_strings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lab_assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("section_id", sa.Uuid(), nullable=False),
        sa.Column("server_id", sa.Uuid(), nullable=True),
        sa.Column("state", sa.String(length=8), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["section_id"], ["sections.id"], name="fk_lab_assignments_section_id_sections", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["server_id"], ["remote_servers.id"], name="fk_lab_assignments_server_id_remote_servers", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lab_assignments_user_id", "lab_assignments", ["user_id"], unique=False)
    op.create_index("ix_lab_assignments_section_id", "lab_assignments", ["section_id"], unique=False)
    op.create_index("ix_lab_assignments_server_id", "lab_assignments", ["server_id"], unique=False)
    op.create_index("ix_lab_assignments_state", "lab_assignments", ["state"], unique=False)
    if op.get_bind().dialect.name == "postgresql" and not context.is_offline_mode():
        op.create_index(
            "uq_lab_assignments_user_section_live",
            "lab_assignments",
            ["user_id", "section_id"],
            unique=True,
            postgresql_where=sa.text("state <> 'RELEASED'"),
        )
        op.create_index(
            "uq_lab_assignments_server_active",
            "lab_assignments",
            ["server_id"],
            unique=True,
            postgresql_where=sa.text("state = 'ACTIVE'"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_index("uq_lab_assignments_server_active", table_name="lab_assignments")
        op.drop_index("uq_lab_assignments_user_section_live", table_name="lab_assignments")
    op.drop_index("ix_lab_assignments_state", table_name="lab_assignments")
    op.drop_index("ix_lab_assignments_server_id", table_name="lab_assignments")
    op.drop_index("ix_lab_assignments_section_id", table_name="lab_assignments")
    op.drop_index("ix_lab_assignments_user_id", table_name="lab_assignments")
    op.drop_table("lab_assignments")
