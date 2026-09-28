"""Dedup + backfill rules untuk 0008_course_lab_access (irreversible)."""

import importlib.util
from pathlib import Path
from uuid import uuid4

import sqlalchemy as sa

_MIGRATION = Path(__file__).parents[3] / "alembic" / "versions" / "0008_course_lab_access.py"


def _load_migration():
    spec = importlib.util.spec_from_file_location("_0008_course_lab_access", _MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _rows():
    return [
        {"user_id": "u1", "course_id": "c1", "server_id": "s-old", "state": "ACTIVE", "updated_at": "2026-01-01"},
        {"user_id": "u1", "course_id": "c1", "server_id": "s-new", "state": "ACTIVE", "updated_at": "2026-02-01"},
        {"user_id": "u1", "course_id": "c1", "server_id": None, "state": "QUEUED", "updated_at": "2026-03-01"},
        {"user_id": "u2", "course_id": "c1", "server_id": None, "state": "QUEUED", "updated_at": "2026-01-01"},
        {"user_id": "u1", "course_id": "c2", "server_id": "s-c2", "state": "QUEUED", "updated_at": "2026-01-01"},
    ]


def test_dedup_keeps_newest_active_with_server():
    migration = _load_migration()
    assert migration.revision == "0008_course_lab_access"
    assert migration.down_revision == "0007_lab_assignments"
    best = migration._survivors(_rows())
    assert best[("u1", "c1")]["row"]["server_id"] == "s-new"
    assert best[("u1", "c2")]["row"]["server_id"] == "s-c2"
    # u2 hanya punya QUEUED tanpa server -> dimenangkan lalu di-skip saat insert
    assert best[("u2", "c1")]["row"]["server_id"] is None


def test_backfill_join_and_insert_on_sqlite():
    """Replika SELECT + INSERT migrasi di atas sqlite: join section->module valid, 1 row per (user, course)."""
    migration = _load_migration()
    engine = sa.create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(sa.text("CREATE TABLE courses (id TEXT PRIMARY KEY)"))
        conn.execute(sa.text("CREATE TABLE modules (id TEXT PRIMARY KEY, course_id TEXT)"))
        conn.execute(sa.text("CREATE TABLE sections (id TEXT PRIMARY KEY, module_id TEXT)"))
        conn.execute(sa.text("CREATE TABLE lab_assignments (id TEXT PRIMARY KEY, user_id TEXT, section_id TEXT, server_id TEXT NULL, state TEXT, created_at TEXT, updated_at TEXT)"))
        conn.execute(
            sa.text(
                "CREATE TABLE course_lab_access (id TEXT PRIMARY KEY, user_id TEXT, course_id TEXT, server_id TEXT NULL, state TEXT, created_at TEXT, updated_at TEXT)"
            )
        )
        c1, c2, m1, m2, s1, s2 = (str(uuid4()) for _ in range(6))
        conn.execute(sa.text("INSERT INTO courses (id) VALUES (:i)"), [{"i": c1}, {"i": c2}])
        conn.execute(sa.text("INSERT INTO modules (id, course_id) VALUES (:i, :c)"), [{"i": m1, "c": c1}, {"i": m2, "c": c2}])
        conn.execute(sa.text("INSERT INTO sections (id, module_id) VALUES (:i, :m)"), [{"i": s1, "m": m1}, {"i": s2, "m": m2}])
        conn.execute(
            sa.text(
                "INSERT INTO lab_assignments (id, user_id, section_id, server_id, state, created_at, updated_at) VALUES (:i, :u, :s, :srv, :st, :c, :up)"
            ),
            [
                {"i": str(uuid4()), "u": "u1", "s": s1, "srv": "srv-old", "st": "ACTIVE", "c": "2026-01-01", "up": "2026-01-01"},
                {"i": str(uuid4()), "u": "u1", "s": s1, "srv": "srv-new", "st": "ACTIVE", "c": "2026-01-02", "up": "2026-02-01"},
                {"i": str(uuid4()), "u": "u1", "s": s2, "srv": "srv-c2", "st": "QUEUED", "c": "2026-01-01", "up": "2026-01-01"},
            ],
        )
        rows = list(
            conn.execute(
                sa.text(
                    "SELECT a.user_id, a.server_id, a.state, a.created_at, a.updated_at,"
                    " m.course_id FROM lab_assignments a"
                    " JOIN sections s ON s.id = a.section_id"
                    " JOIN modules m ON m.id = s.module_id"
                    " WHERE a.state <> 'RELEASED'"
                )
            ).mappings()
        )
        inserted = 0
        for (user_id, course_id), entry in migration._survivors(rows).items():
            row = entry["row"]
            if row["server_id"] is None:
                continue
            conn.execute(
                sa.text(
                    "INSERT INTO course_lab_access (id, user_id, course_id, server_id, state, created_at, updated_at)"
                    " VALUES (:id, :user_id, :course_id, :server_id, 'ACTIVE', :created_at, :updated_at)"
                ),
                {"id": str(uuid4()), "user_id": user_id, "course_id": course_id, "server_id": row["server_id"], "created_at": row["created_at"], "updated_at": row["updated_at"]},
            )
            inserted += 1
        assert inserted == 2
        by_course = {(r.user_id, r.course_id): r.server_id for r in conn.execute(sa.text("SELECT user_id, course_id, server_id FROM course_lab_access")).mappings()}
        assert by_course == {("u1", c1): "srv-new", ("u1", c2): "srv-c2"}
