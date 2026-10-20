"""course-scoped lab access, drop server-spec settings

Revision ID: 0008_course_lab_access
Revises: 0007_lab_assignments

Irreversible data migration (accepted 2026-09-28): legacy
lab_environment_settings are discarded and per-section lab_assignments
are deduped to one ACTIVE row per (user, course).
"""
from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa


revision: str = "0008_course_lab_access"
down_revision: Union[str, None] = "0007_lab_assignments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "course_lab_access",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("server_id", sa.Uuid(), nullable=True),
        sa.Column("state", sa.String(length=8), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], name="fk_course_lab_access_course_id_courses", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["server_id"], ["remote_servers.id"], name="fk_course_lab_access_server_id_remote_servers", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_course_lab_access_user_id", "course_lab_access", ["user_id"], unique=False)
    op.create_index("ix_course_lab_access_course_id", "course_lab_access", ["course_id"], unique=False)
    op.create_index("ix_course_lab_access_server_id", "course_lab_access", ["server_id"], unique=False)
    op.create_index("ix_course_lab_access_state", "course_lab_access", ["state"], unique=False)
    bind = op.get_bind()
    if bind.dialect.name == "postgresql" and not context.is_offline_mode():
        op.create_index(
            "uq_course_lab_access_user_course_live",
            "course_lab_access",
            ["user_id", "course_id"],
            unique=True,
            postgresql_where=sa.text("state = 'ACTIVE'"),
        )
        op.create_index(
            "uq_course_lab_access_server_active",
            "course_lab_access",
            ["server_id"],
            unique=True,
            postgresql_where=sa.text("state = 'ACTIVE'"),
        )

    _backfill_course_access(bind)

    if bind.dialect.name == "postgresql" and not context.is_offline_mode():
        op.drop_index("uq_lab_assignments_server_active", table_name="lab_assignments")
        op.drop_index("uq_lab_assignments_user_section_live", table_name="lab_assignments")
    op.drop_index("ix_lab_assignments_state", table_name="lab_assignments")
    op.drop_index("ix_lab_assignments_server_id", table_name="lab_assignments")
    op.drop_index("ix_lab_assignments_section_id", table_name="lab_assignments")
    op.drop_index("ix_lab_assignments_user_id", table_name="lab_assignments")
    op.drop_table("lab_assignments")

    op.drop_index("ix_lab_environment_settings_section_id", table_name="lab_environment_settings")
    op.drop_index("ix_lab_environment_settings_slug", table_name="lab_environment_settings")
    op.drop_table("lab_environment_settings")
    op.execute("DELETE FROM content_slug_registry WHERE content_kind = 'lab_environment_settings'")


def _backfill_course_access(bind) -> None:
    del bind
    op.execute(
        "WITH ranked_assignments AS ("
        " SELECT a.user_id, a.server_id, a.state, a.created_at, a.updated_at, m.course_id,"
        " row_number() OVER (PARTITION BY a.user_id, m.course_id"
        " ORDER BY (a.state = 'ACTIVE') DESC, (a.server_id IS NOT NULL) DESC, a.updated_at DESC) AS rank"
        " FROM lab_assignments a"
        " JOIN sections s ON s.id = a.section_id"
        " JOIN modules m ON m.id = s.module_id"
        " WHERE a.state <> 'RELEASED'"
        ") INSERT INTO course_lab_access"
        " (id, user_id, course_id, server_id, state, created_at, updated_at)"
        " SELECT gen_random_uuid(), user_id, course_id, server_id, 'ACTIVE', created_at, updated_at"
        " FROM ranked_assignments WHERE rank = 1 AND server_id IS NOT NULL"
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_index("uq_course_lab_access_server_active", table_name="course_lab_access")
        op.drop_index("uq_course_lab_access_user_course_live", table_name="course_lab_access")
    op.drop_index("ix_course_lab_access_state", table_name="course_lab_access")
    op.drop_index("ix_course_lab_access_server_id", table_name="course_lab_access")
    op.drop_index("ix_course_lab_access_course_id", table_name="course_lab_access")
    op.drop_index("ix_course_lab_access_user_id", table_name="course_lab_access")
    op.drop_table("course_lab_access")
    # Legacy data is NOT restored (irreversible by design). Recreate empty
    # legacy tables so schema downgrade stays consistent.
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
