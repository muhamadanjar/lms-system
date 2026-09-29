# Tasks: Bulk Enrollment

**Input**: Design documents from `specs/006-bulk-enrollment/`

**Tests**: Required (fake directory, MockTransport adapter, HTTP contracts).

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup

- [X] T001 Record git status baseline (004+005 committed?) in specs/006-bulk-enrollment/tasks.md

## Phase 2: Foundational

**⚠️ CRITICAL**: Blocks all stories.

- [X] T002 Create UserDirectory port + errors in app/application/ports/user_directory.py
- [X] T003 [P] Create UM search adapter in app/infrastructure/auth/usermanagement_directory.py (exact-match, envelope-tolerant, timeout→unavailable)
- [X] T004 [P] Adapter unit tests with httpx MockTransport in tests/unit/infrastructure/test_usermanagement_directory.py

## Phase 3: US1 — Bulk enroll (P1) 🎯 MVP

**Independent Test**: Mixed batch → 207 buckets correct, no duplicates on repeat.

### Tests (write FIRST, FAIL before implementation)

- [X] T005 [P] [US1] App tests with fake directory in tests/unit/application/test_bulk_enrollment.py

### Implementation

- [X] T006 [US1] Implement bulk_enroll() in app/application/use_cases/enrollment.py (single UoW, dedup, per-item isolation)
- [X] T007 [US1] Bulk schemas in app/presentation/schemas/enrollment.py + POST /bulk (207, editor-only) in app/presentation/routers/enrollments.py with directory factory + bearer forwarding
- [X] T008 [US1] HTTP bulk tests (207 shape, 403 learner, 422 over-limit) in tests/contract/http/test_enrollments.py (extend)

**Checkpoint**: US1 green independently

## Phase 4: US2 — Email resolution (P1)

**Independent Test**: Exact/unknown/ambiguous/down → enrolled/NOT_FOUND/AMBIGUOUS/DIRECTORY_UNAVAILABLE.

- [X] T009 [P] [US2] Email-path app tests (fake directory behaviors) in tests/unit/application/test_bulk_enrollment.py (extend)
- [X] T010 [US2] HTTP email test with monkeypatched directory factory in tests/contract/http/test_enrollments.py (extend)

**Checkpoint**: US1+US2 green

## Phase 5: Polish

- [X] T011 Update docs/api-roles.md (bulk row + curl example)
- [X] T012 Full suite + compileall + domain purity + mark tasks [X]

## Dependencies

Sequential T001→T012 except T003∥T004. Tests before code per story.
