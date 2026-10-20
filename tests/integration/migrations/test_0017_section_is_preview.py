"""Verify the additive Section preview flag migration and its rollback."""

import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

_MIGRATION = (
    Path(__file__).parents[3]
    / "alembic"
    / "versions"
    / "0017_section_is_preview.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location("_0017_section_is_preview", _MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_existing_sections_default_preview_disabled_and_migration_rolls_back():
    migration = _load_migration()
    engine = sa.create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(sa.text("CREATE TABLE sections (id INTEGER PRIMARY KEY)"))
        conn.execute(sa.text("INSERT INTO sections (id) VALUES (1), (2)"))
        with Operations.context(MigrationContext.configure(conn)):
            migration.upgrade()
        values = conn.execute(sa.text("SELECT is_preview FROM sections ORDER BY id")).scalars().all()
        assert values == [0, 0]

        with Operations.context(MigrationContext.configure(conn)):
            migration.downgrade()
        assert "is_preview" not in {column["name"] for column in sa.inspect(conn).get_columns("sections")}
    engine.dispose()
