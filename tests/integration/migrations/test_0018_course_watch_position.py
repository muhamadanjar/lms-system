"""Verify the additive Enrollment resume-position migration and rollback."""

import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

_MIGRATION = (
    Path(__file__).parents[3]
    / "alembic"
    / "versions"
    / "0018_course_watch_position.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location("_0018_course_watch_position", _MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_enrollment_position_is_nullable_and_migration_rolls_back():
    migration = _load_migration()
    engine = sa.create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(sa.text("CREATE TABLE sections (id CHAR(32) PRIMARY KEY)"))
        conn.execute(sa.text("CREATE TABLE enrollments (id CHAR(32) PRIMARY KEY)"))
        conn.execute(sa.text("INSERT INTO sections (id) VALUES ('section-a')"))
        conn.execute(sa.text("INSERT INTO enrollments (id) VALUES ('enrollment-a')"))
        with Operations.context(MigrationContext.configure(conn)):
            migration.upgrade()

        column = next(
            item
            for item in sa.inspect(conn).get_columns("enrollments")
            if item["name"] == "last_opened_section_id"
        )
        assert column["nullable"] is True
        assert conn.execute(
            sa.text("SELECT last_opened_section_id FROM enrollments")
        ).scalar_one() is None
        foreign_keys = sa.inspect(conn).get_foreign_keys("enrollments")
        assert any(
            key["referred_table"] == "sections"
            and key["constrained_columns"] == ["last_opened_section_id"]
            for key in foreign_keys
        )

        with Operations.context(MigrationContext.configure(conn)):
            migration.downgrade()
        assert "last_opened_section_id" not in {
            column["name"] for column in sa.inspect(conn).get_columns("enrollments")
        }
    engine.dispose()
