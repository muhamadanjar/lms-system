# Tasks: Course Progression and Collect Tasks

**Input**: [spec.md](spec.md), [plan.md](plan.md), [data-model.md](data-model.md), [contracts](contracts/)

**Organization**: Ordered by dependencies. Regression tests are required by the repository's AGENTS.md for course, quiz, and lab changes.

## Phase 1: Persistence Foundation

- [x] T001 [P] Add domain policy types/default validation for Course progression and completion modes and Section pass policy in `app/domain/entities/`.
- [x] T002 [P] Add `SectionCompletion`, `CollectTask`, and immutable task event domain behavior in `app/domain/entities/`.
- [x] T003 Add ORM columns and tables with constraints/indexes in `app/infrastructure/persistence/models/`.
- [x] T004 Add forward/reverse Alembic migration; existing Courses backfill to `ADMIN_REVIEW`, progression defaults `FREE`, section pass defaults false, quiz passing score defaults 70.
- [x] T005 Add mapper and repository ports/adapters for learner completion and task history.
- [x] T006 Wire repositories through `UnitOfWorkPort`, SQLModel UoW, and composition root.
- [x] T007 Add domain and persistence regression tests for defaults, constraints, task transitions, history, and migration upgrade/downgrade.

## Phase 2: US1 — Configure Course Progression

- [x] T008 [P] [US1] Extend course and section request/response schemas with mode and `requires_pass` settings.
- [x] T009 [US1] Persist Course/Section configuration through existing editor use cases and routers.
- [x] T010 [US1] Add configurable quiz passing score, default 70, to quiz authoring validation and persistence mapping.
- [x] T011 [US1] Add HTTP contract tests for editor authorization, defaults, validation, and round trips.

## Phase 3: US2 — Enforce Learner Progress and Completion

- [x] T012 [P] [US2] Implement domain progression and course eligibility policies covering text, ordinary quiz, lab, and excluded exam sections.
- [x] T013 [US2] Add application use cases to calculate learner section state and mark text completion.
- [x] T014 [US2] Enforce sequential access for section list/detail and quiz sitting start; omit locked section body and identify blocker.
- [x] T015 [US2] Connect finalized ordinary quiz result/pass percentage to learner progress and retry until pass; preserve exam max-attempt behavior.
- [x] T016 [US2] Automatically complete eligible self-learning enrollment; guard admin completion for admin-review courses with the same eligibility policy.
- [x] T017 [US2] Add progression, quiz pass threshold, completion mode, and enrollment regression tests.

## Phase 4: US3 — Submit and Review CollectTask

- [x] T018 [US3] Add learner task submission/read use cases with text and HTTP(S) link validation and ownership checks.
- [x] T019 [US3] Add administrator queue, begin-review, pass, and revision-request use cases with reviewer identity and score/note validation.
- [x] T020 [US3] Add authenticated HTTP schemas/routes for learner and administrator task operations.
- [x] T021 [US3] Integrate task review outcomes with completion eligibility while allowing navigation past labs.
- [x] T022 [US3] Add task lifecycle, authorization, history immutability, completion, and HTTP contract regression tests.

## Phase 5: Polish and Verification

- [x] T023 Review diff for preserved pre-existing user changes, answer-key/learner-data confidentiality, and domain dependency direction.
- [ ] T024 Run formatter, linter, type/import checks and focused unit, application, HTTP, and migration verification available in the repository.
- [x] T025 Update API documentation and record verification limits in the implementation handoff.

Verification notes: `tests/unit` passes (120 tests); migration, persistence, and progression/file HTTP tests pass (43 tests). Alembic upgrade and downgrade SQL generation both pass offline; dependency check, compileall, and `git diff --check` pass. Ruff is unavailable in the environment. Full suite was not rerun; an earlier suite run stalled at the unrelated auth contract test `test_missing_token_returns_401_without_calling_auth_service`. Online PostgreSQL migration execution was not available.

## Phase 6: Learner Task Files

- [x] T026 [US3] Add private `Files` metadata and a version-aware M2M association to CollectTask submission history with migration and registry wiring.
- [x] T027 [US3] Add local and S3-compatible object storage adapters, environment configuration, and private download authorization for task owner/admin/instructor.
- [x] T028 [US3] Add multipart task submission with file count/size/type validation while preserving the existing JSON evidence-link route.
- [x] T029 [US3] Add unit, persistence, migration, and HTTP regression tests for storage, revision retention, and access control.
- [x] T030 [US3] Update specification, data model, and HTTP contract for task file upload behavior.
