"""Verify the additive course_instructors migration and its rollback."""

import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

_MIGRATION = Path(__file__).parents[3] / "alembic" / "versions" / "0020_course_instructors.py"


def _load_migration():
    spec = importlib.util.spec_from_file_location("_0020_course_instructors", _MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_course_instructors_created_with_unique_pair_and_rolls_back():
    migration = _load_migration()
    engine = sa.create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "CREATE TABLE courses (id CHAR(36) PRIMARY KEY)"
            )
        )
        conn.execute(sa.text("INSERT INTO courses (id) VALUES ('c1')"))
        with Operations.context(MigrationContext.configure(conn)):
            migration.upgrade()

        inspector = sa.inspect(conn)
        columns = {column["name"] for column in inspector.get_columns("course_instructors")}
        assert {"id", "user_id", "course_id", "created_at", "updated_at"}.issubset(columns)

        with Operations.context(MigrationContext.configure(conn)):
            conn.execute(
                sa.text(
                    "INSERT INTO course_instructors (id, user_id, course_id, created_at, updated_at) "
                    "VALUES ('i1', 'u1', 'c1', '2024-01-01 00:00:00', '2024-01-01 00:00:00')"
                )
            )
            try:
                conn.execute(
                    sa.text(
                        "INSERT INTO course_instructors (id, user_id, course_id, created_at, updated_at) "
                        "VALUES ('i2', 'u1', 'c1', '2024-01-01 00:00:00', '2024-01-01 00:00:00')"
                    )
                )
                raise AssertionError("duplicate course_id+user_id must be rejected")
            except sa.exc.IntegrityError:
                pass

        with Operations.context(MigrationContext.configure(conn)):
            migration.downgrade()
        assert "course_instructors" not in sa.inspect(conn).get_table_names()
    engine.dispose()
