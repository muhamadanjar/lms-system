# Tasks: Course Enrollment

**Input**: Design documents from `specs/005-course-enrollment/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Required — constitution + AGENTS.md mandate regression tests for enrollment, gate, cascade.

**Organization**: Grouped by user story; each story independently testable.

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Baseline before additive change

- [X] T001 Record git status baseline and confirm 004 suites green in specs/005-course-enrollment/tasks.md
- [X] T002 [P] Confirm alembic head is 0008_course_lab_access via alembic history in specs/005-course-enrollment/tasks.md

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Enrollment domain core + table + migration that all stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 Create pure domain entity Enrollment + EnrollmentStatus in app/domain/entities/enrollment.py (complete()/withdraw(), tz-aware checks)
- [X] T004 [P] Create repository port EnrollmentRepository in app/domain/repositories/enrollment.py
- [X] T005 [P] Create SQLModel table Enrollment in app/infrastructure/persistence/models/enrollment.py (course FK CASCADE, partial unique live)
- [X] T006 [P] Create enrollment mapper in app/infrastructure/persistence/mappers/enrollment_mapper.py
- [X] T007 Create SqlModelEnrollmentRepository in app/infrastructure/persistence/repositories/enrollment_repository.py (create/get_live/update/list_live_by_course/list_history)
- [X] T008 Rewire SqlModelUnitOfWork + UnitOfWorkPort in app/infrastructure/persistence/unit_of_work.py + app/application/ports/unit_of_work.py (add enrollments) and register model in app/infrastructure/persistence/model_registry.py
- [X] T009 Create alembic 0009_course_enrollment.py (create enrollments + indexes, drop on downgrade)

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Learner enrolls in a course (Priority: P1) 🎯 MVP

**Goal**: Enroll/my-enrollment/list per course with idempotency and self-or-editor auth

**Independent Test**: Enroll U in C, re-enroll returns same row, my-enrollment reads it, cross-user enroll denied

### Tests for User Story 1

> NOTE: Write these tests FIRST, ensure they FAIL before implementation

- [X] T010 [P] [US1] Domain tests for Enrollment invariants in tests/unit/domain/test_enrollment.py
- [X] T011 [P] [US1] Application tests for enroll idempotency + backdate rules with fake ports in tests/unit/application/test_enrollment.py
- [X] T012 [P] [US1] Persistence tests for partial unique + cascade in tests/integration/persistence/test_enrollment.py
- [X] T013 [P] [US1] HTTP contract tests per contracts/enrollment.http.md in tests/contract/http/test_enrollments.py

### Implementation for User Story 1

- [X] T014 [US1] Implement EnrollmentUseCases (enroll/my_enrollment/list_course_enrollments) in app/application/use_cases/enrollment.py
- [X] T015 [US1] Create EnrollmentRead/Create schemas in app/presentation/schemas/enrollment.py
- [X] T016 [US1] Create enrollments router (POST enroll, GET me, GET list) in app/presentation/routers/enrollments.py and register in app/main.py

**Checkpoint**: US1 fully functional and testable independently

---

## Phase 4: User Story 2 - Lab access requires enrollment (Priority: P1)

**Goal**: Lab enroll denied without live enrollment (403 ENROLLMENT_REQUIRED)

**Independent Test**: Lab enroll without enrollment → 403; enroll course → lab enroll → 201

### Tests for User Story 2

- [X] T017 [P] [US2] Gate tests (app fake + HTTP 403 code) in tests/unit/application/test_enrollment.py + tests/contract/http/test_enrollments.py (extend, not new files)

### Implementation for User Story 2

- [X] T018 [US2] Add live-enrollment gate in app/application/use_cases/lab_enrollment.py enroll() + map ENROLLMENT_REQUIRED in app/presentation/exception_handlers.py

**Checkpoint**: US1 AND US2 both work

---

## Phase 5: User Story 3 - Complete or withdraw with lab side effects (Priority: P2)

**Goal**: complete() stamps completed_at and keeps lab; withdraw() releases lab VPS; re-enroll creates new row; course delete cascades

**Independent Test**: Withdraw holder → server reusable; complete holder → lab still opens; re-enroll → new row; delete course → enrollments gone

### Tests for User Story 3

- [X] T019 [P] [US3] Lifecycle tests (complete/withdraw/re-enroll/cascade) in tests/unit/application/test_enrollment.py + tests/integration/persistence/test_enrollment.py + tests/contract/http/test_enrollments.py (extend)

### Implementation for User Story 3

- [X] T020 [US3] Implement complete/withdraw (with lab release via UoW) in app/application/use_cases/enrollment.py + router endpoints in app/presentation/routers/enrollments.py
- [X] T021 [US3] Cascade-delete enrollments in app/infrastructure/persistence/repositories/course_repository.py delete()

**Checkpoint**: All stories independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Prove migration + contracts + no placeholders

- [X] T022 [P] Update migration chain assertions in tests/integration/migrations/test_migrations.py (add 0009) + registry assertions in tests/integration/migrations/test_model_registry.py (add enrollments)
- [X] T023 Run full quickstart validation (new suites + alembic upgrade head + heads + rg for progress/grade/role in enrollment files) in specs/005-course-enrollment/quickstart.md
- [X] T024 Run compileall + domain purity check per AGENTS.md and record results in specs/005-course-enrollment/tasks.md

---

## Dependencies & Execution Order

- **Setup → Foundational → US1 → US2 → US3 → Polish** (sequential; US2 edits lab_enrollment which US1 tests cover; US3 extends US1 files)
- Tests MUST be written and FAIL before implementation in each story
- T010 ∥ T011 ∥ T012 ∥ T013; T022 ∥ T023-prep allowed after US3 green

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Setup + Foundational → enroll/my/list usable, lab untouched
2. STOP and VALIDATE US1 independently

### Incremental Delivery

1. US1 → roster works
2. US2 → lab gate live (behavioral change, release-noted)
3. US3 → lifecycle + cascade complete
