"""create course module section hierarchy

Revision ID: 0001_initial_content_hierarchy
Revises:
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial_content_hierarchy"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _status() -> sa.String:
    return sa.String(length=9)


def _timestamps(table: sa.Table) -> None:
    table.append_column(sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    table.append_column(sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))


def upgrade() -> None:
    op.create_table(
        "courses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("status", _status(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_courses"),
    )
    op.create_index("ix_courses_slug", "courses", ["slug"], unique=False)

    op.create_table(
        "content_slug_registry",
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("content_id", sa.Uuid(), nullable=False),
        sa.Column("content_kind", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("slug", name="pk_content_slug_registry"),
    )
    op.create_index("ix_content_slug_registry_content_id", "content_slug_registry", ["content_id"], unique=False)

    op.create_table(
        "modules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("status", _status(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], name="fk_modules_course_id_courses", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_modules"),
        sa.UniqueConstraint("course_id", "position", name="uq_modules_course_position"),
    )
    op.create_index("ix_modules_slug", "modules", ["slug"], unique=False)
    op.create_index("ix_modules_course_id", "modules", ["course_id"], unique=False)

    op.create_table(
        "sections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("status", _status(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("module_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("content_type", sa.String(length=10), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["module_id"], ["modules.id"], name="fk_sections_module_id_modules", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_sections"),
        sa.UniqueConstraint("module_id", "position", name="uq_sections_module_position"),
    )
    op.create_index("ix_sections_slug", "sections", ["slug"], unique=False)
    op.create_index("ix_sections_module_id", "sections", ["module_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_sections_module_id", table_name="sections")
    op.drop_index("ix_sections_slug", table_name="sections")
    op.drop_table("sections")
    op.drop_index("ix_modules_course_id", table_name="modules")
    op.drop_index("ix_modules_slug", table_name="modules")
    op.drop_table("modules")
    op.drop_index("ix_content_slug_registry_content_id", table_name="content_slug_registry")
    op.drop_table("content_slug_registry")
    op.drop_index("ix_courses_slug", table_name="courses")
    op.drop_table("courses")
