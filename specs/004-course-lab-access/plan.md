# Implementation Plan: Course Lab Access

**Branch**: `004-course-lab-access` | **Date**: 2026-09-28 | **Spec**: specs/004-course-lab-access/spec.md

**Input**: Feature specification from `specs/004-course-lab-access/spec.md`

## Summary

Replace per-section lab assignments plus per-section server-spec settings with one live `CourseLabAccess` per (user, course) backed by the existing `remote_servers` inventory. Learners read task instructions from section body and open the same VPS from any lab section in the course via server-side SSH; no credentials ever reach the learner. Migration is intentionally irreversible: drop `lab_environment_settings`, re-scope assignments to `course_id`, dedup legacy rows keeping the most recently active.

## Technical Context

**Language/Version**: Python 3.11 (pinned deps: FastAPI 0.141, SQLModel 0.0.46, SQLAlchemy 2.0.54, Alembic 1.16.5)

**Primary Dependencies**: FastAPI + Pydantic v2, SQLModel/SQLAlchemy, Alembic, asyncssh (console PTY), httpx (user-management auth), pydantic-settings; stdlib `abc`/`typing.Protocol` for ports — no new packages

**Storage**: PostgreSQL (prod) / SQLite + aiosqlite (tests) via SQLModel; Alembic versions `0002`, `0006`, `0007` touch lab tables; new `0008_course_lab_access` required

**Testing**: pytest + pytest-asyncio; layers: `tests/unit/domain`, `tests/unit/application` (fake ports), `tests/integration/persistence`, `tests/contract/http`, `tests/contract/websocket`

**Target Platform**: Linux server (uvicorn + FastAPI + WebSocket console)

**Project Type**: web-service (Clean Architecture: presentation → application → domain ← infrastructure)

**Performance Goals**: Enroll idempotent under concurrent double-enroll (one row wins); console keeps single-active-session-per-server with takeover; my-lab read is single indexed lookup by (user, course)

**Constraints**: Domain stays pure Python (no FastAPI/SQLModel/Pydantic-transport imports); learner responses/logs/errors MUST NOT contain secrets or answer keys; authorization enforced in application use cases; irreversible migration MUST be documented with recovery note

**Scale/Scope**: Courses with N lab sections share 1 access per learner; dedup migration over legacy (user, section) rows; capacity failure is explicit, no queue

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] I. Domain-Driven Learning Model — **CONFLICT DOCUMENTED**: constitution says Lab Quiz owns VPS config/spec; this feature supersedes it (instructions stay in section body, no spec object). Resolved via explicit migration task + spec 004 as amendment basis. No new ubiquitous terms beyond `CourseLabAccess` (course-scoped access).
- [x] II. Clean Architecture — domain entity `CourseLabAccess` pure; repository port owned by domain/application; routers map errors only, never touch aggregates.
- [x] III. Ports/adapters & packages — reuse `RemoteServerRepository`, SSH bridge, cipher, UoW; no new dependency; delete dead wrappers (`LabEnvironmentSettings` entity/model/repo/use-case, queue helpers).
- [x] IV. Testable workflows — domain tests without DB; app tests with fake ports (success/duplicate/capacity/release + isolation); persistence tests for unique (user,course) + server-exclusivity + migration dedup; HTTP contract for my-lab/enroll/release + error mapping; WS contract re-scoped to course access; secret-scan regression.
- [x] V. Security/observability — secrets only in `remote_servers` ciphertext; learner DTO has `server_id` but no credential; structured logs redact; metrics preserved (request failure, provisioning/enrollment failure, console failure).
- [x] Workflow gates — plan → tasks → implement; migration irreversible is allowed only with documented recovery (rebuild settings impossible by design; assignments dedup rule recorded in `data-model.md` + `quickstart.md`); breaking API change ships with compatibility note (old `/lab` settings paths removed).

Post-design re-check: no new folders without consumer; `lab_management.py`/`lab_settings.py` either deleted or repurposed with active consumer only; `LabProvisioner` spec ideal stays unimplemented — no placeholder provisioning abstraction is added.

## Project Structure

### Documentation (this feature)

```text
specs/004-course-lab-access/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── lab-access.http.md
└── tasks.md
```

### Source Code (repository root)

```text
app/
├── domain/entities/course_lab_access.py      # NEW: pure access entity (replaces lab_assignment.py)
├── domain/repositories/course_lab_access.py  # NEW: port (replaces assignment repo port if any)
├── application/use_cases/lab_enrollment.py   # REWORK: course-scoped enroll/release/my-lab
├── infrastructure/persistence/models/course_lab_access.py  # NEW: table course_lab_access
├── infrastructure/persistence/repositories/course_lab_access_repository.py  # NEW
├── infrastructure/persistence/unit_of_work.py # REWIRE: assignments -> lab_access
├── presentation/routers/course_labs.py       # NEW: /api/courses/{slug}/lab/my-lab + enroll/release
├── presentation/routers/labs.py              # DELETE lab-settings + per-section assignment endpoints
├── presentation/websocket/console.py         # REWORK: user_may_open_console via course access
└── presentation/schemas/lab_access.py        # NEW: CourseLabAccessRead (no queue_position, no secrets)

alembic/versions/0008_course_lab_access.py    # NEW: drop settings, migrate assignments -> course access
tests/
├── unit/domain/test_course_lab_access.py
├── unit/application/test_course_lab_enrollment.py
├── integration/persistence/test_course_lab_access.py
├── integration/migrations/test_0008_course_lab_access.py
├── contract/http/test_course_lab_access.py
└── contract/websocket/test_console_course_access.py

DELETED (no consumer after refactor):
app/domain/entities/lab_environment.py, app/domain/entities/lab_assignment.py,
app/infrastructure/persistence/models/lab_environment_settings.py,
app/infrastructure/persistence/models/lab_assignment.py,
app/infrastructure/persistence/repositories/lab_environment_repository.py,
app/infrastructure/persistence/repositories/lab_assignment_repository.py,
app/application/use_cases/lab_settings.py, app/application/use_cases/lab_management.py (if unused),
tests for the above + old contract tests referencing them
```

**Structure Decision**: Keep layer-direct layout under `app/` (no new bounded-context folder). One entity + one repository + one use-case + one router for the feature; every new file has an active consumer (router → use-case → port → repository → model). Deletions happen in the same change as their replacements.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Irreversible migration (settings data unrecoverable) | Grill decision 2026-09-28: server-spec concept is removed by design, keeping a reversible downgrade would preserve dead semantics | Reversible downgrade would require re-creating spec validation, repos, and endpoints slated for deletion |
| Constitution conflict (Lab Quiz no longer owns VPS config) | Learner flow needs zero server-spec management; inventory + course access covers real usage | Keeping spec-per-section preserves the redundancy the feature exists to remove |
