"""course-scoped lab access, drop server-spec settings

Revision ID: 0008_course_lab_access
Revises: 0007_lab_assignments

Irreversible data migration (accepted 2026-09-28): legacy
lab_environment_settings are discarded and per-section lab_assignments
are deduped to one ACTIVE row per (user, course).
"""
from typing import Sequence, Union
from uuid import uuid4

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
    bind.execute(sa.text("DELETE FROM content_slug_registry WHERE content_kind = 'lab_environment_settings'"))


def _survivors(rows) -> dict[tuple[str, str], dict]:
    """Satu pemenang per (user, course): ACTIVE > QUEUED, berserver, terbaru."""
    best: dict[tuple[str, str], dict] = {}
    for row in rows:
        key = (row["user_id"], str(row["course_id"]))
        active = 1 if row["state"] == "ACTIVE" else 0
        has_server = 1 if row["server_id"] is not None else 0
        candidate = (active, has_server, str(row["updated_at"]))
        current = best.get(key)
        if current is None or candidate > current["rank"]:
            best[key] = {"rank": candidate, "row": row}
    return best


def _backfill_course_access(bind) -> None:
    rows = list(
        bind.execute(
            sa.text(
                "SELECT a.user_id, a.server_id, a.state, a.created_at, a.updated_at,"
                " m.course_id FROM lab_assignments a"
                " JOIN sections s ON s.id = a.section_id"
                " JOIN modules m ON m.id = s.module_id"
                " WHERE a.state <> 'RELEASED'"
            )
        ).mappings()
    )
    for (user_id, course_id), entry in _survivors(rows).items():
        row = entry["row"]
        if row["server_id"] is None:
            continue
        bind.execute(
            sa.text(
                "INSERT INTO course_lab_access (id, user_id, course_id, server_id, state, created_at, updated_at)"
                " VALUES (:id, :user_id, :course_id, :server_id, 'ACTIVE', :created_at, :updated_at)"
            ),
            {
                "id": str(uuid4()),
                "user_id": user_id,
                "course_id": course_id,
                "server_id": str(row["server_id"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            },
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
