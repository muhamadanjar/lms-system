"""store persisted enum values as strings

Revision ID: 0006_store_enums_as_strings
Revises: 0005_add_content
"""

from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa


revision: str = "0006_store_enums_as_strings"
down_revision: Union[str, None] = "0005_add_content"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CONTENT_STATUS_TABLES = (
    "answers",
    "courses",
    "lab_environment_settings",
    "modules",
    "questions",
    "quiz_sittings",
    "quizzes",
    "sections",
)


def _content_status() -> sa.Enum:
    return sa.Enum("DRAFT", "PUBLISHED", "ARCHIVED", name="contentstatus")


def _access_method() -> sa.Enum:
    return sa.Enum("PASSWORD", "PUBLIC_KEY", name="accessmethod")


def upgrade() -> None:
    """Replace native enums left by an older migration with VARCHAR storage."""
    bind = op.get_bind()
    if bind.dialect.name != "postgresql" or context.is_offline_mode():
        return

    content_status = _content_status()
    access_method = _access_method()
    enum_names = {enum["name"] for enum in sa.inspect(bind).get_enums()}

    if "contentstatus" in enum_names:
        for table_name in CONTENT_STATUS_TABLES:
            op.alter_column(
                table_name,
                "status",
                existing_type=content_status,
                type_=sa.String(length=9),
                postgresql_using=f"{table_name}.status::varchar(9)",
                existing_nullable=False,
            )
        content_status.drop(bind, checkfirst=True)

    if "accessmethod" in enum_names:
        op.alter_column(
            "remote_servers",
            "access_method",
            existing_type=access_method,
            type_=sa.String(length=11),
            postgresql_using="remote_servers.access_method::varchar(11)",
            existing_nullable=False,
        )
        access_method.drop(bind, checkfirst=True)


def downgrade() -> None:
    """Keep VARCHAR storage, which is also the preceding revision's schema."""
