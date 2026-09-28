# Tasks: Course Lab Access

**Input**: Design documents from `specs/004-course-lab-access/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Required — constitution + AGENTS.md mandate regression tests for lab/access/migration/secret-leak paths.

**Organization**: Grouped by user story; each story independently testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1/US2/US3 maps to spec.md stories in priority order

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Baseline before destructive refactor

- [X] T001 Verify git status clean and record baseline in specs/004-course-lab-access/tasks.md
- [X] T002 [P] Run baseline lab-related suites to record pre-change state (pytest tests/unit tests/contract/http/test_lab_enrollments.py tests/integration/persistence/test_lab_environment_settings.py)
- [X] T003 [P] Confirm current head is 0007_lab_assignments via alembic history in specs/004-course-lab-access/tasks.md

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: New domain core + migration skeleton that all stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Create pure domain entity CourseLabAccess in app/domain/entities/course_lab_access.py (ACTIVE/RELEASED, release(), touch())
- [X] T005 [P] Create repository port CourseLabAccessRepository in app/domain/repositories/course_lab_access.py
- [X] T006 [P] Create SQLModel table CourseLabAccess in app/infrastructure/persistence/models/course_lab_access.py (course_id FK courses.id CASCADE, server_id FK remote_servers.id SET NULL, partial uniques)
- [X] T007 Create SqlModelCourseLabAccessRepository in app/infrastructure/persistence/repositories/course_lab_access_repository.py (create/get_live/list_live_by_course/list_live_by_user/find_active_by_server/free_server_ids/update)
- [X] T008 Rewire SqlModelUnitOfWork in app/infrastructure/persistence/unit_of_work.py (assignments -> lab_access) keeping old attribute as deprecated alias only if needed by migration
- [X] T009 Register model in app/infrastructure/persistence/model_registry.py (add CourseLabAccess, keep old names only until migration lands)
- [X] T010 Create alembic 0008_course_lab_access.py skeleton (create table + indexes, empty data migration placeholder) in alembic/versions/0008_course_lab_access.py

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Learner uses one VPS per course (Priority: P1) 🎯 MVP

**Goal**: Enroll returns one access per (user, course); my-lab reads it from any section; second course gets different server

**Independent Test**: Enroll learner in course with 2 lab sections, open my-lab from both, verify same server_id; enroll same learner in second course, verify different server_id

### Tests for User Story 1

> NOTE: Write these tests FIRST, ensure they FAIL before implementation

- [X] T011 [P] [US1] Domain tests for CourseLabAccess invariants in tests/unit/domain/test_course_lab_access.py
- [X] T012 [P] [US1] Application tests for enroll idempotency + my-lab + cross-course isolation with fake ports in tests/unit/application/test_course_lab_enrollment.py
- [X] T013 [P] [US1] Persistence tests for unique (user,course) live + server exclusivity in tests/integration/persistence/test_course_lab_access.py
- [X] T014 [P] [US1] HTTP contract tests for my-lab/enroll per contracts/lab-access.http.md in tests/contract/http/test_course_lab_access.py

### Implementation for User Story 1

- [X] T015 [US1] Rework LabEnrollmentUseCases to course scope in app/application/use_cases/lab_enrollment.py (enroll/release/my_lab/list_course_accesses/user_has_course_server; drop queue_position + section fan-out)
- [X] T016 [US1] Create CourseLabAccessRead schema in app/presentation/schemas/lab_access.py (no section_id/queue_position/secrets)
- [X] T017 [US1] Create course lab router in app/presentation/routers/course_labs.py (GET my-lab, POST enroll, DELETE release) and register in app/main.py
- [X] T018 [US1] Map application errors to HTTP codes per contracts/lab-access.http.md in app/presentation/routers/course_labs.py

**Checkpoint**: US1 fully functional and testable independently

---

## Phase 4: User Story 2 - Admin provides VPS access (Priority: P2)

**Goal**: Capacity-aware assignment from remote_servers pool; release frees server; legacy data migrated with dedup

**Independent Test**: Seed pool of 1 server, enroll 2 learners (second gets 409 CAPACITY_EXHAUSTED with no row); release first, re-enroll second (succeeds); migrate legacy multi-section rows (one live survives)

### Tests for User Story 2

- [X] T019 [P] [US2] Capacity + release application tests in tests/unit/application/test_course_lab_enrollment.py (extend, not new file)
- [X] T020 [P] [US2] Migration test with legacy lab_assignments fixtures in tests/integration/migrations/test_0008_course_lab_access.py

### Implementation for User Story 2

- [X] T021 [US2] Complete backfill + drops in alembic/versions/0008_course_lab_access.py (course_lab_access create, legacy join sections->modules->courses dedup ACTIVE-newest, drop lab_assignments + lab_environment_settings + slug reservations)
- [X] T022 [US2] Delete legacy lab settings stack (app/domain/entities/lab_environment.py, app/infrastructure/persistence/models/lab_environment_settings.py, app/infrastructure/persistence/repositories/lab_environment_repository.py, app/application/use_cases/lab_settings.py, app/application/use_cases/lab_management.py if orphaned, typed_content_mapper lab branches)
- [X] T023 [US2] Delete legacy assignment stack (app/domain/entities/lab_assignment.py, app/infrastructure/persistence/models/lab_assignment.py, app/infrastructure/persistence/repositories/lab_assignment_repository.py) and remove per-section lab routers in app/presentation/routers/labs.py + assignment mapping in app/presentation/routers/enrollments.py + schemas in app/presentation/schemas/content.py

**Checkpoint**: US1 AND US2 both work; no legacy lab tables or settings endpoints remain

---

## Phase 5: User Story 3 - Never expose credentials (Priority: P1 security)

**Goal**: Server-side SSH preserved; console auth re-scoped to course access; secrets absent from learner surfaces

**Independent Test**: Secret-scan enroll + my-lab + WS error frames + logs for seeded secrets; unrelated learner denied on чужой server_id

### Tests for User Story 3

- [X] T024 [P] [US3] WS contract test for course-scoped console auth in tests/contract/websocket/test_console_course_access.py
- [X] T025 [P] [US3] Secret-redaction test for CourseLabAccess rows/responses/logs in tests/integration/persistence/test_secret_redaction.py (extend)

### Implementation for User Story 3

- [X] T026 [US3] Re-scope user_may_open_console to course access in app/presentation/websocket/console.py (replace LabEnrollmentUseCases.user_has_active_server with user_has_course_server)
- [X] T027 [US3] Audit learner DTO + error mapping for secret leakage in app/presentation/schemas/lab_access.py and app/presentation/routers/course_labs.py

**Checkpoint**: All stories independently functional; security slice green

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Remove residue, prove migration + contracts

- [X] T028 [P] Delete/update stale tests referencing lab_environment_settings/lab_assignment/queue_position (tests/integration/persistence/test_lab_environment_settings.py, test_section_content_types.py, test_enum_storage.py, tests/contract/http/test_lab_enrollments.py, tests/integration/migrations/test_model_registry.py, tests/integration/migrations/test_migrations.py head assertion)
- [X] T029 [P] Update model registry + migration head assertions + docs release note for breaking API and irreversible migration in specs/004-course-lab-access/quickstart.md
- [X] T030 Run full quickstart validation (pytest suites + alembic upgrade head + alembic check + rg for lab_environment_settings|queue_position|password_secret_ref outside 0008) in specs/004-course-lab-access/quickstart.md
- [X] T031 Run formatter/linter/type-check/import-check per AGENTS.md and record results in specs/004-course-lab-access/tasks.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Stories (Phase 3+)**: Depend on Foundational; US1 → US2 → US3 sequentially (US2 deletes legacy code US1 no longer needs; US3 re-scopes console onto US1 access)
- **Polish (Phase 6)**: Depends on all stories complete

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models/ports before repository before use-case before router
- Migration backfill (T021) after repository (T007) so dedup rule is testable
- Deletions (T022/T023) after replacements (T015-T018) are green

### Parallel Opportunities

- T002 ∥ T003; T005 ∥ T006; T011 ∥ T012 ∥ T013 ∥ T014; T019 ∥ T020; T024 ∥ T025; T028 ∥ T029
- All [P] tasks touch different files

---

## Parallel Example: User Story 1

```bash
# Launch all US1 tests together:
Task: "Domain tests in tests/unit/domain/test_course_lab_access.py"
Task: "Application tests in tests/unit/application/test_course_lab_enrollment.py"
Task: "Persistence tests in tests/integration/persistence/test_course_lab_access.py"
Task: "HTTP contract tests in tests/contract/http/test_course_lab_access.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 + Phase 2
2. Complete Phase 3 (US1) — enroll/my-lab course-scoped alongside legacy code behind new router
3. STOP and VALIDATE US1 independently before deletions

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. US1 → deploy/demo (new course-lab path usable)
3. US2 → migration + deletions (legacy removed)
4. US3 → console re-scope + secret audit (security gate)
5. Polish → quickstart green, release notes

---

## Notes

- Exact file paths are normative; do not create files outside plan.md structure decision.
- T021 downgrade recreates empty legacy tables only — document as irreversible in release notes.
- Stop at each checkpoint and validate the story independently before proceeding.
