# Implementation Plan: Course Enrollment

**Branch**: `005-course-enrollment` | **Date**: 2026-09-28 | **Spec**: specs/005-course-enrollment/spec.md

**Input**: Feature specification from `specs/005-course-enrollment/spec.md`

## Summary

Add a course-participant record (`Enrollment`: one live `ENROLLED` per user+course with history rows, backdatable `enrolled_at`, `completed_at` on completion) that gates the existing course lab access: lab enroll requires live enrollment, withdrawal auto-releases the lab VPS. Pure additive change on top of 004 plus a gate check and a withdrawal side effect; no changes to server inventory or console behavior.

## Technical Context

**Language/Version**: Python 3.12 (pinned deps: FastAPI 0.141, SQLModel 0.0.46, SQLAlchemy 2.0.54, Alembic 1.16.5)

**Primary Dependencies**: FastAPI + Pydantic v2, SQLModel/SQLAlchemy, Alembic; pytest + pytest-asyncio; no new packages

**Storage**: PostgreSQL (prod) / SQLite + aiosqlite (tests); new `0009_course_enrollment` migration creating `enrollments`

**Testing**: pytest (asyncio_mode=auto); layers: `tests/unit/domain`, `tests/unit/application` (fake ports), `tests/integration/persistence`, `tests/contract/http`

**Target Platform**: Linux server (uvicorn + FastAPI)

**Project Type**: web-service (presentation → application → domain ← infrastructure)

**Performance Goals**: Enroll idempotent under concurrent double-enroll (one live row wins via partial unique index); my-enrollment is a single indexed lookup

**Constraints**: Domain stays pure Python; authorization in application use cases; router self-or-editor rule mirrors lab enroll; no secrets involved; migration additive (no data rewrite)

**Scale/Scope**: One table, one use-case, one router, one migration; touches `LabEnrollmentUseCases.enroll` (gate) and course delete cascade

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] I. Domain model — new `Enrollment` entity with explicit states; `enrolled_at`/`completed_at` invariants in domain, not routers. No new ubiquitous terms beyond Enrollment.
- [x] II. Clean Architecture — entity pure; `EnrollmentRepository` port; router maps errors only; lab gate enforced inside application use case, not router.
- [x] III. Ports/packages — one new port with SQLModel adapter + fake for tests; no new dependency.
- [x] IV. Tests — domain invariant tests; app tests with fakes (enroll idempotency, gate denial, withdraw-releases-lab, complete-keeps-lab); persistence tests (partial unique, cascade); HTTP contracts (enroll/my/complete/withdraw + lab gate 403/409 mapping).
- [x] V. Security — self-or-editor authorization; no secrets in this slice; course delete cascades enrollments.
- [x] Workflow — additive migration (reversible: drop table); breaking aspect is behavioral only for lab enroll without enrollment (documented in release note + quickstart).

Post-design re-check: every new file has an active consumer; no placeholder fields (progress/grade/role rejected in grill).

## Project Structure

### Documentation (this feature)

```text
specs/005-course-enrollment/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── enrollment.http.md
└── tasks.md
```

### Source Code (repository root)

```text
app/
├── domain/entities/enrollment.py                 # NEW: pure entity + EnrollmentStatus
├── domain/repositories/enrollment.py             # NEW: port
├── application/use_cases/enrollment.py           # NEW: enroll/my/complete/withdraw/list
├── application/use_cases/lab_enrollment.py       # EDIT: gate on live enrollment; withdraw path releases lab
├── infrastructure/persistence/models/enrollment.py
├── infrastructure/persistence/mappers/enrollment_mapper.py
├── infrastructure/persistence/repositories/enrollment_repository.py
├── infrastructure/persistence/unit_of_work.py    # ADD enrollments repo
├── infrastructure/persistence/model_registry.py  # ADD Enrollment
├── infrastructure/persistence/repositories/course_repository.py  # cascade delete enrollments
├── presentation/schemas/enrollment.py            # NEW: EnrollmentRead/Create/Complete
├── presentation/routers/enrollments.py           # NEW: /api/courses/{slug}/enrollments (enroll/my/list/complete/withdraw)
└── presentation/exception_handlers.py            # EDIT: ENROLLMENT_REQUIRED mapping (if distinct code needed)

alembic/versions/0009_course_enrollment.py        # NEW: create enrollments
tests/
├── unit/domain/test_enrollment.py
├── unit/application/test_enrollment.py
├── integration/persistence/test_enrollment.py
└── contract/http/test_enrollments.py
```

**Structure Decision**: Same layer-direct layout as 004. New `enrollments.py` router name is free again (old per-section file was deleted in 004).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Lab enroll behavior change (now requires enrollment) | Grill decision: gate gives enrollment meaning and protects VPS pool | Independent roster would leave enrollment without an active consumer, violating the no-placeholder rule |
