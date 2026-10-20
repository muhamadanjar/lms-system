"""Exercise the set-based backfill used by the irreversible 0008 migration."""

import importlib.util
from pathlib import Path
from uuid import uuid4

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

_MIGRATION = Path(__file__).parents[3] / "alembic" / "versions" / "0008_course_lab_access.py"


def _load_migration():
    spec = importlib.util.spec_from_file_location("_0008_course_lab_access", _MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_backfill_uses_latest_server_per_user_course_on_sqlite():
    migration = _load_migration()
    engine = sa.create_engine("sqlite://")
    with engine.begin() as conn:
        conn.connection.create_function("gen_random_uuid", 0, lambda: str(uuid4()))
        conn.execute(sa.text("CREATE TABLE courses (id TEXT PRIMARY KEY)"))
        conn.execute(sa.text("CREATE TABLE modules (id TEXT PRIMARY KEY, course_id TEXT)"))
        conn.execute(sa.text("CREATE TABLE sections (id TEXT PRIMARY KEY, module_id TEXT)"))
        conn.execute(sa.text("CREATE TABLE lab_assignments (id TEXT PRIMARY KEY, user_id TEXT, section_id TEXT, server_id TEXT NULL, state TEXT, created_at TEXT, updated_at TEXT)"))
        conn.execute(sa.text("CREATE TABLE course_lab_access (id TEXT PRIMARY KEY, user_id TEXT, course_id TEXT, server_id TEXT NULL, state TEXT, created_at TEXT, updated_at TEXT)"))

        c1, c2, m1, m2, s1, s2 = (str(uuid4()) for _ in range(6))
        conn.execute(sa.text("INSERT INTO courses (id) VALUES (:i)"), [{"i": c1}, {"i": c2}])
        conn.execute(sa.text("INSERT INTO modules (id, course_id) VALUES (:i, :c)"), [{"i": m1, "c": c1}, {"i": m2, "c": c2}])
        conn.execute(sa.text("INSERT INTO sections (id, module_id) VALUES (:i, :m)"), [{"i": s1, "m": m1}, {"i": s2, "m": m2}])
        conn.execute(
            sa.text("INSERT INTO lab_assignments (id, user_id, section_id, server_id, state, created_at, updated_at) VALUES (:i, :u, :s, :srv, :st, :c, :up)"),
            [
                {"i": str(uuid4()), "u": "u1", "s": s1, "srv": "srv-old", "st": "ACTIVE", "c": "2026-01-01", "up": "2026-01-01"},
                {"i": str(uuid4()), "u": "u1", "s": s1, "srv": "srv-new", "st": "ACTIVE", "c": "2026-01-02", "up": "2026-02-01"},
                {"i": str(uuid4()), "u": "u1", "s": s2, "srv": "srv-c2", "st": "QUEUED", "c": "2026-01-01", "up": "2026-01-01"},
                {"i": str(uuid4()), "u": "u2", "s": s1, "srv": None, "st": "QUEUED", "c": "2026-01-01", "up": "2026-01-01"},
            ],
        )

        with Operations.context(MigrationContext.configure(conn)):
            migration._backfill_course_access(conn)

        by_course = {
            (row.user_id, row.course_id): row.server_id
            for row in conn.execute(sa.text("SELECT user_id, course_id, server_id FROM course_lab_access")).mappings()
        }
        assert by_course == {("u1", c1): "srv-new", ("u1", c2): "srv-c2"}
    engine.dispose()
