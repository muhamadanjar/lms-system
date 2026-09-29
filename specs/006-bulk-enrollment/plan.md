# Implementation Plan: Bulk Enrollment

**Branch**: `006-bulk-enrollment` | **Date**: 2026-09-28 | **Spec**: specs/006-bulk-enrollment/spec.md

**Input**: Feature specification from `specs/006-bulk-enrollment/spec.md`

## Summary

Add editor-only `POST /api/courses/{slug}/enrollments/bulk` (max 100, 207 per-item results) on top of 005: entries carry `user_id` and/or `email`; emails resolve to canonical ids through a new `UserDirectory` port backed by UM `GET /users?search=` (exact case-insensitive single match, caller bearer forwarded). Single transaction, no lab side effects.

## Technical Context

**Language/Version**: Python 3.12 (FastAPI 0.141, SQLModel 0.0.46, SQLAlchemy 2.0.54, Alembic 1.16.5)

**Primary Dependencies**: FastAPI + Pydantic v2, httpx (UM lookup, existing dep, timeout from `UserManagementSettings`); no new packages

**Storage**: No migration (reuses `enrollments` table + partial unique index for race safety)

**Testing**: pytest (asyncio_mode=auto); unit app with fake directory; infra unit with httpx MockTransport; HTTP contract with monkeypatched directory factory

**Target Platform**: Linux server (uvicorn + FastAPI)

**Project Type**: web-service (presentation → application → domain ← infrastructure)

**Performance Goals**: ≤100 lookups sequential per request; UM timeout 3s default bounds worst case; single DB transaction per bulk

**Constraints**: Domain stays pure (directory port lives in application layer); bearer forwarded, never logged; duplicate live races resolved via get_live re-check after ConflictError

**Scale/Scope**: One port + one adapter + use-case method + endpoint + schemas; docs/api-roles.md updated

## Constitution Check

- [x] I. Domain model — no domain changes; bulk orchestration in application use case reusing `Enrollment` invariants.
- [x] II. Clean Architecture — `UserDirectory` port owned by application (`app/application/ports/`), adapter in infrastructure; router maps errors only.
- [x] III. Ports/packages — one narrow port; httpx already a baseline dep with active consumer.
- [x] IV. Tests — fake directory app tests; MockTransport adapter tests; HTTP 207/403/422 contracts.
- [x] V. Security — editor-only; bearer forwarded server-side, never in logs/responses; emails only used for lookup, stored id only.
- [x] Workflow — no migration; additive endpoint; release note in quickstart.

## Project Structure

### Documentation (this feature)

```text
specs/006-bulk-enrollment/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── bulk-enrollment.http.md
└── tasks.md
```

### Source Code (repository root)

```text
app/
├── application/ports/user_directory.py        # NEW: UserDirectory + EmailNotFound/Ambiguous/Unavailable
├── application/use_cases/enrollment.py        # ADD: bulk_enroll()
├── infrastructure/auth/usermanagement_directory.py  # NEW: UM search adapter
├── presentation/schemas/enrollment.py         # ADD: bulk schemas
├── presentation/routers/enrollments.py        # ADD: POST /bulk (207, editor-only)
docs/api-roles.md                             # EDIT: bulk row + curl
tests/
├── unit/application/test_bulk_enrollment.py   # NEW (fake directory)
├── unit/infrastructure/test_usermanagement_directory.py  # NEW (MockTransport)
└── contract/http/test_enrollments.py          # EXTEND: bulk 207/403/422
```

**Structure Decision**: Port in application (not domain) since directory lookup is an application-service concern, not a domain invariant.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Sequential UM lookups (no batch endpoint) | UM only exposes single search; ≤100 with 3s timeout is acceptable | Parallel fan-out adds failure complexity for an admin-paced flow |
