# Quickstart: Course Module Section Persistence

This guide validates the implemented persistence slice. Migration bodies remain versioned under
`alembic/versions/` and the application uses them instead of runtime `create_all`.

## Prerequisites

- Python 3.12 environment with project dependencies installed.
- PostgreSQL available for integration tests.
- `DATABASE__URL` configured for the test database, or the project's equivalent database
  settings.
- `aiosqlite` is available for local async SQLite smoke tests; PostgreSQL remains the source of
  truth for integration behavior.
- Secret manager test double configured for lab credential reference tests.

The implementation adds `alembic`, `asyncpg`, `pytest`, and `pytest-asyncio` only when the
corresponding migration, async repository, and test code is introduced.

## Schema Validation

From the repository root:

```bash
alembic upgrade head
alembic check
alembic downgrade -1
alembic upgrade head
```

Expected outcomes:

- All feature tables and named constraints exist after `upgrade head`.
- `alembic check` reports no uncommitted metadata difference.
- Downgrade removes the feature schema cleanly and a second upgrade recreates it.

## Automated Tests

```bash
pytest -q tests/unit/domain tests/unit/application
pytest -q tests/integration/persistence tests/integration/migrations
pytest -q tests/contract/http
pytest -q tests/unit tests/integration
pytest -q tests/contract/http
```

The PostgreSQL integration suite MUST run with foreign-key enforcement and verify behavior that
SQLite cannot reliably represent. SQLite may be used for fast repository unit fixtures only.

The local suite uses a synchronous SQLite driver behind an async-shaped fixture adapter because
SQLite is only a smoke-test backend. Production request sessions use SQLAlchemy async sessions
with `asyncpg`.

This repository currently has no checked-in formatter, linter, or type-checker configuration and
the corresponding executables are not installed in `venv`; the final local verification therefore
uses `compileall`, pytest, `git diff --check`, and Alembic schema checks. Add the project's selected
tooling before enforcing those gates in CI.

## Required Validation Scenarios

1. Create a Course, ordered Modules, and ordered Sections; reload by Course slug and verify
   `position, id` ordering.
2. Attempt duplicate Module/Section positions and confirm an atomic rollback.
3. Create `MATERIAL`, `LAB_TASK`, and `QUIZ` Sections; reject mismatched detail models.
4. Create LabEnvironmentSettings with password and public-key modes; verify only secret
   references are stored and raw credentials never appear in logs or responses.
5. Create a Quiz with MULTICHOICE and DIRECT Questions, normalized Answers, and positive
   instructor weights.
6. Create a QuizSitting and verify `IN_PROGRESS → SUBMITTED → GRADED` transitions and invalid
   transition rejection.
7. Attempt duplicate or changed slugs across different model tables and confirm global
   conflict/immutability behavior.
8. Delete a Course and a Module directly through the repository and verify all descendants,
   detail rows, and active slug registry entries are removed atomically.
9. Verify all new records default to `DRAFT`, timestamps are UTC-aware, and `created_at` is
   immutable.
10. Run `tests/contract/http/test_content_crud.py` to verify Course → Module → Section CRUD,
    nested slug ownership, PATCH, hierarchy read, and DELETE through FastAPI.
11. Verify `USERMANAGEMENT__BASE_URL`, `USERMANAGEMENT__AUTH_INFO_PATH`, and
    `USERMANAGEMENT__TIMEOUT_SECONDS` point to the User Management `/auth/info` integration.

## Manual Inspection

- Confirm Alembic `env.py` imports the model registry before assigning `target_metadata`.
- Confirm application startup attaches the database lifespan to `FastAPI(lifespan=lifespan)`.
- Confirm domain modules do not import SQLModel, SQLAlchemy, FastAPI, or Pydantic transport
  schemas.
- Confirm no migration or fixture contains raw VPS password/private-key material.
- Confirm the model registry contains all nine persistence tables and `alembic check` reports no
  schema drift.
