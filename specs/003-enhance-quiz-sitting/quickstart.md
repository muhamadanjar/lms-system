# Quickstart: Enhanced Quiz Sitting Results

This guide validates the quiz-sitting feature after implementation. It complements the
[data model](data-model.md) and [HTTP contract](contracts/http.md); it does not replace their
invariants.

## Prerequisites

- Python 3.12 environment and project requirements installed.
- A database configured through the project environment. PostgreSQL is required for production
  migration/concurrency evidence; the current synchronous SQLite fixture remains a fast smoke
  test only.
- A reachable User Management `/auth/info` service or the project test authentication override.
- A seeded published Course → Module → Quiz Section with an authorized learner and content
  editor.

## Schema and Migration Validation

Run the repository's migration checks after adding the new revision:

```bash
alembic upgrade head
alembic check
alembic downgrade -1
alembic upgrade head
```

Expected results:

1. Legacy Questions receive deterministic unique `Q-######` codes and retain prompt, type,
   options, status, and ordering.
2. The allocator's next generated code is greater than every backfilled generated suffix.
3. Quiz configuration, snapshot, selection, result, active-draft, and exam-counter storage is
   present after upgrade.
4. Downgrade removes new dependent data in safe order; take a backup before using this recovery
   procedure in a non-disposable database.

## Focused Automated Tests

```bash
pytest -q tests/unit/domain/test_question_code.py tests/unit/domain/test_quiz_sitting_results.py
pytest -q tests/unit/application/test_quiz_sitting_use_cases.py
pytest -q tests/integration/persistence/test_quiz_models.py tests/integration/persistence/test_quiz_sitting_lifecycle.py
pytest -q tests/integration/migrations/test_migrations.py tests/integration/migrations/test_quiz_sitting_backfill.py
pytest -q tests/contract/http/test_quiz_sittings.py
pytest -q
```

Run the relevant commands inside the application container when the service is running in
Docker. Report a focused SQLite result separately from PostgreSQL upgrade/downgrade and
concurrency verification.

## Implementation Evidence (2026-09-28)

- Focused unit, application, persistence, migration-registry, and HTTP commands for this
  feature pass locally (the US1-focused command reports `9 passed`). The HTTP checks include
  answer-key redaction and rejection of mutations after finalization.
- `python -m compileall -q app alembic`, OpenAPI route inspection, and `git diff --check`
  pass locally. Eight OpenAPI paths contain the quiz workflow.
- The local Docker daemon has no LMS application container, so PostgreSQL
  upgrade/downgrade/upgrade and concurrent-finalization evidence has not been run. The full
  suite also stops during collection because the existing SSH integration test requires an
  unavailable `asyncssh` package. Neither condition is evidence that the feature is broken;
  both remain release gates for the deployment environment.
- `DIRECT` questions remain stored for compatibility, but starting a quiz sitting containing
  one is rejected with `422` until its scoring policy is specified.

## Required End-to-End Scenarios

1. Author creates a Question without a code and receives a generated `Q-######` code. Create
   another with a manual code, then confirm case- or whitespace-equivalent input is rejected.
2. Publish a Question, then confirm its code cannot change. Confirm a draft code can change only
   to another globally unique normalized value.
3. Learner starts a multiple-choice sitting. Confirm a second start resumes the same draft and
   that the response exposes no correct option marker.
4. Save one correct, one incorrect, and leave one question unanswered. Finalize and verify the
   three required code lists partition the available codes, every code has a score entry, and
   the total is their sum.
5. Retry finalization after the saved result and confirm identical result identity/content with
   no second history entry. Simulate a failure before commit and confirm the sitting remains
   retryable without final results.
6. Change the source Question or its options after sitting start; finalize/retrieve the sitting
   and confirm its snapshot/result stays unchanged.
7. For an exam defaulting to one attempt, finalize once then confirm the next finalization is
   refused. Repeat with `max_attempts: 3`; verify the fourth finalization is refused even under
   competing requests.
8. For a non-exam, finalize two sittings with different totals and confirm both remain in
   history while the summary returns the highest score.
9. Attempt to read a sitting as another learner and confirm `404`. Inspect final learner
   responses and structured logs to confirm they contain neither answer keys nor selected
   option values.

## Completion Checks

- Run `git diff --check`.
- Confirm generated OpenAPI includes Bearer security and the routes in
  [contracts/http.md](contracts/http.md).
- Confirm no domain module imports FastAPI, Pydantic transport schemas, SQLModel, SQLAlchemy,
  database drivers, or HTTP clients.
- Record whether PostgreSQL migration and concurrency tests were executed; do not treat health
  checks or SQLite smoke tests as proof of production behavior.
