# Quickstart: Course Lab Access validation

**Spec**: specs/004-course-lab-access/spec.md | **Plan**: specs/004-course-lab-access/plan.md

## Prerequisites

- Python env with `pytest pytest-asyncio`, DB reachable (SQLite default for quick checks).
- Seed: one course with 2 lab sections, `remote_servers` pool ≥ 2, two learner ids.

## Run

```bash
pytest tests/unit/domain/test_course_lab_access.py -q
pytest tests/unit/application/test_course_lab_enrollment.py -q
pytest tests/integration/persistence/test_course_lab_access.py -q
pytest tests/contract/http/test_course_lab_access.py -q
pytest tests/contract/websocket/test_console_course_access.py -q
alembic upgrade head && alembic check
pytest tests/integration/migrations/test_0008_course_lab_access.py -q
rg -n "password_secret_ref|private_key_secret_ref|lab_environment_settings|queue_position" app tests --glob '*.py' | grep -v 0008 | grep -v test_legacy || true
```

Expected: all suites green; final `rg` shows no references outside the migration + its dedicated legacy test; `alembic check` clean.

## Manual end-to-end (happy path)

1. `POST /api/courses/{slug}/lab/enroll {"user_id":"u1"}` → 201 with `course_id`, `server_id`, `state=ACTIVE`.
2. `POST` again same user+course → same row (no duplicate).
3. `GET /api/courses/{slug}/lab/my-lab` as u1 → same `server_id` from either lab section page.
4. Enroll u1 in a second course → different `server_id`.
5. Open `WS /api/v1/servers/{server_id}/console` as u1 → `ready`; as unrelated u2 → `closed auth_error`.
6. `DELETE /api/courses/{slug}/lab/release/u1` → released; server becomes free for the next enroll.
7. Exhaust pool then enroll → `409 CAPACITY_EXHAUSTED`, no row created.

## Recovery note (irreversible migration)

- `alembic downgrade -1` recreates empty legacy tables only; dropped settings and deduped assignments are NOT restored — accepted per grill 2026-09-28. Backup before upgrading production.
