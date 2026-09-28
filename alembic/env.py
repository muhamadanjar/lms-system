from logging.config import fileConfig
import re
from collections.abc import Iterable

from alembic import context
from alembic.operations import MigrationScript
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import engine_from_config, pool

from app.config.config import get_settings
from app.infrastructure.persistence.model_registry import metadata

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
database_url = settings.database.get_database_url(sync=True)
config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
target_metadata = metadata

REVISION_ID_PATTERN = re.compile(r"(?P<number>\d{4})_[a-z0-9_]+$")
REVISION_MESSAGE_PATTERN = re.compile(r"[^a-z0-9]+")


def _next_numeric_revision_id() -> str:
    """Return the next four-digit revision number from the active migration chain."""
    revisions = ScriptDirectory.from_config(config).walk_revisions()
    numbers = (
        int(match.group("number"))
        for revision in revisions
        if (match := REVISION_ID_PATTERN.fullmatch(revision.revision)) is not None
    )
    return f"{max(numbers, default=0) + 1:04d}"


def _revision_message_slug(message: str | None) -> str:
    """Normalize a revision message for its stable ID and filename suffix."""
    slug = REVISION_MESSAGE_PATTERN.sub("_", (message or "").lower()).strip("_")
    if not slug:
        raise RuntimeError("a migration message is required for numeric revision naming")
    return slug


def assign_numeric_revision_id(
    migration_context: MigrationContext,
    revision: str | Iterable[str | None] | Iterable[str],
    directives: list[MigrationScript],
) -> None:
    """Force newly generated revisions to use the project's numeric ID convention."""
    del migration_context, revision
    if len(directives) != 1:
        raise RuntimeError("numeric revision naming supports exactly one migration directive")
    directive = directives[0]
    directive.rev_id = f"{_next_numeric_revision_id()}_{_revision_message_slug(directive.message)}"


def run_migrations_offline() -> None:
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        process_revision_directives=assign_numeric_revision_id,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            process_revision_directives=assign_numeric_revision_id,
        )
        with context.begin_transaction():
            context.run_migrations()
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
