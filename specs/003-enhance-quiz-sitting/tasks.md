# Tasks: Enhanced Quiz Sitting Results

**Input**: Design documents from `specs/003-enhance-quiz-sitting/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [HTTP contract](contracts/http.md), and
[quickstart.md](quickstart.md)

**Tests**: Required. The feature specification and constitution require domain, application,
persistence/migration, and HTTP regression coverage. Write each listed test before its matching
implementation and verify it fails for the expected missing behavior before turning it green.

**Organization**: Tasks are grouped by user story. Shared schema/domain work is in the
foundational phase because every story relies on the same immutable question-code and sitting
snapshot model.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because the task touches different files with no unfinished
  dependency.
- **[Story]**: Maps the task to a user story from [spec.md](spec.md).

## Phase 1: Setup (Shared Test Infrastructure)

**Purpose**: Establish isolated test support without changing production behavior.

- [X] T001 Create unit-test package markers in `tests/unit/domain/__init__.py` and `tests/unit/application/__init__.py`.
- [X] T002 [P] Create reusable fake repositories, authorization context, and Unit of Work in `tests/unit/application/fakes.py` for quiz-sitting use-case tests.
- [X] T003 [P] Extend baseline migration revision assertions in `tests/integration/migrations/test_migrations.py` to accept the next quiz-sitting-results revision after it is added.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create the domain, persistence, and migration seams required by every user story.

**⚠️ CRITICAL**: Complete this phase before user-story implementation begins.

- [X] T004 Add `QuestionCode`, `AnswerPolicy`, and question-result outcome value objects with normalization and validation in `app/domain/value_objects/quiz_assessment.py`.
- [X] T005 Extend aggregate invariants for quiz configuration, draft/published question-code mutability, and final sitting immutability in `app/domain/entities/quiz.py`, `app/domain/entities/question.py`, and `app/domain/entities/quiz_sitting.py`.
- [X] T006 Add snapshot, selection, result, and learner-safe result-projection domain entities in `app/domain/entities/quiz_sitting_snapshot.py`.
- [X] T007 Add exact-set multiple-choice evaluation and full result-partition validation in `app/domain/services/quiz_evaluation.py`.
- [X] T008 Define focused domain repository and code-allocation contracts in `app/domain/repositories/quiz_assessment.py` and expose typed quiz/sitting properties in `app/application/ports/unit_of_work.py`.
- [X] T009 [P] Add SQLModel tables for the code allocator, sitting snapshots, snapshot options, selections, question results, and exam counters in `app/infrastructure/persistence/models/question_code_sequence.py`, `app/infrastructure/persistence/models/quiz_sitting_question.py`, `app/infrastructure/persistence/models/quiz_sitting_option.py`, `app/infrastructure/persistence/models/quiz_sitting_answer_selection.py`, `app/infrastructure/persistence/models/quiz_sitting_question_result.py`, and `app/infrastructure/persistence/models/quiz_exam_attempt_counter.py`.
- [X] T010 Extend existing SQLModel fields/constraints for quiz configuration, normalized global question code, active draft key, and final total score in `app/infrastructure/persistence/models/quiz.py`, `app/infrastructure/persistence/models/question.py`, and `app/infrastructure/persistence/models/quiz_sitting.py`.
- [X] T011 Register new persistence tables and mappings in `app/infrastructure/persistence/model_registry.py` and `app/infrastructure/persistence/mappers/typed_content_mapper.py`.
- [X] T012 Implement transactional SQLModel code allocation, snapshot persistence, selection/result persistence, active-draft lookup, and locked exam-attempt counter access in `app/infrastructure/persistence/repositories/quiz_repository.py` and `app/infrastructure/persistence/repositories/quiz_sitting_repository.py`.
- [X] T013 Wire the concrete repositories into the Unit of Work in `app/infrastructure/persistence/unit_of_work.py`.
- [X] T014 Add reversible schema/backfill migration for configuration, question codes, allocator state, snapshot/result records, active-draft key, and exam counters in `alembic/versions/0004_quiz_sitting_results.py`.
- [X] T015 Update table-registry and migration-chain expectations for the new schema in `tests/integration/migrations/test_model_registry.py` and `tests/integration/migrations/test_migrations.py`.

**Checkpoint**: Domain and persistence foundation supports an immutable, transactionally
finalizable sitting; user-story work may begin.

---

## Phase 3: User Story 1 - Finalize a quiz with auditable results (Priority: P1) 🎯 MVP

**Goal**: Learners can finalize a multiple-choice sitting and retrieve immutable code lists,
per-question scores, and total score without answer-key leakage.

**Independent Test**: Finalize a snapshot with correct, wrong, and unanswered questions; verify
the three lists partition every code, scores are 1/0, subsequent quiz edits have no effect, and
a repeated finalization returns the same saved result.

### Tests for User Story 1

- [X] T016 [P] [US1] Add QuestionCode snapshot partition, exact multi-answer evaluation, 1/0 scoring, total, and final immutability tests in `tests/unit/domain/test_quiz_sitting_results.py`.
- [ ] T017 [P] [US1] Add start/resume, selection validation, atomic finalization, pre-commit failure, idempotent retry, ownership, and answer-key-redaction use-case tests in `tests/unit/application/test_quiz_sitting_use_cases.py`.
- [ ] T018 [P] [US1] Extend snapshot/result round-trip and source-quiz-edit regression coverage in `tests/integration/persistence/test_quiz_models.py` and `tests/integration/persistence/test_quiz_sitting_lifecycle.py`.
- [ ] T019 [P] [US1] Add learner start/save/finalize/get contract, response-envelope, 401/404/422, and no-answer-key tests in `tests/contract/http/test_quiz_sittings.py`.

### Implementation for User Story 1

- [X] T020 [US1] Define start, save-selection, finalize, result, and result-summary command/query DTOs in `app/application/dto/quiz_sittings.py`.
- [X] T021 [US1] Implement application authorization, start-or-resume, snapshot creation, draft selection save, atomic finalization, and learner-safe result reads in `app/application/use_cases/quiz_sittings.py`.
- [X] T022 [US1] Add request/response schemas that exclude answer keys and raw final selections in `app/presentation/schemas/quiz_sittings.py`.
- [X] T023 [US1] Implement learner sitting endpoints from `contracts/http.md` in `app/presentation/routers/quizzes.py` using one application use case per primary operation.
- [X] T024 [US1] Register the quiz router and application dependencies in `app/main.py` and `app/presentation/dependencies/quiz_sittings.py`.
- [X] T025 [US1] Run `tests/unit/domain/test_quiz_sitting_results.py`, `tests/unit/application/test_quiz_sitting_use_cases.py`, `tests/integration/persistence/test_quiz_models.py`, `tests/integration/persistence/test_quiz_sitting_lifecycle.py`, and `tests/contract/http/test_quiz_sittings.py` and resolve only User Story 1 failures.

**Checkpoint**: A learner can complete and retrieve one safe, auditable multiple-choice result
independently of author-managed manual codes and exam limits.

---

## Phase 4: User Story 2 - Manage unique question codes (Priority: P1)

**Goal**: Content authors receive generated codes or submit manual codes that are globally
unique, normalized, and immutable after publication; legacy data is backfilled safely.

**Independent Test**: Create a generated and a manual code, reject normalized duplicates,
reject a published-code change, and upgrade a seeded legacy database without changing question
content or correct-answer policy.

### Tests for User Story 2

- [X] T026 [P] [US2] Add QuestionCode blank-generation, trim/uppercase normalization, global-duplicate, and published-immutability tests in `tests/unit/domain/test_question_code.py`.
- [ ] T027 [P] [US2] Add code-allocation reservation/retry and author authorization use-case tests in `tests/unit/application/test_quiz_question_codes.py`.
- [ ] T028 [P] [US2] Add database uniqueness and deterministic legacy-backfill upgrade/downgrade tests in `tests/integration/persistence/test_question_codes.py` and `tests/integration/migrations/test_quiz_sitting_backfill.py`.
- [X] T029 [P] [US2] Add generated/manual question-code authoring HTTP contract tests in `tests/contract/http/test_quiz_question_codes.py`.

### Implementation for User Story 2

- [ ] T030 [US2] Implement Question create/update code assignment, conflict translation, and published-code guard in `app/application/use_cases/quiz_questions.py`.
- [X] T031 [US2] Add author-facing question-code schemas with optional manual input and normalized output in `app/presentation/schemas/quiz_questions.py`.
- [X] T032 [US2] Add nested quiz-question create/update routes with content-editor authorization in `app/presentation/routers/quizzes.py`.
- [ ] T033 [US2] Verify the migration backfill, code sequence state, and authoring flows with `tests/unit/domain/test_question_code.py`, `tests/unit/application/test_quiz_question_codes.py`, `tests/integration/persistence/test_question_codes.py`, `tests/integration/migrations/test_quiz_sitting_backfill.py`, and `tests/contract/http/test_quiz_question_codes.py`.

**Checkpoint**: Authors can use stable globally unique question codes, and existing Questions
are compatible before this feature's results are relied upon.

---

## Phase 5: User Story 3 - Enforce quiz attempt policy (Priority: P2)

**Goal**: Non-exam quizzes preserve unlimited history and use best score; exams enforce their
configured final-attempt maximum, defaulting to one, even under concurrent requests.

**Independent Test**: Finalize multiple non-exam sittings and verify best score/history; for
exam defaults and a configured maximum, verify the next concurrent finalization is refused.

### Tests for User Story 3

- [X] T034 [P] [US3] Add exam-default, positive-max-attempt, configuration-lock, non-exam-unlimited, and best-score domain tests in `tests/unit/domain/test_quiz_attempt_policy.py`.
- [ ] T035 [P] [US3] Add application tests for exam counter transaction behavior, exhausted-limit error, non-exam history, and best-score summary in `tests/unit/application/test_quiz_attempt_policy.py`.
- [ ] T036 [P] [US3] Add persistence concurrency and one-active-draft constraint regressions in `tests/integration/persistence/test_quiz_attempt_policy.py`.
- [ ] T037 [P] [US3] Add exam configuration, exhausted-limit, non-exam repeat, and summary HTTP contract tests in `tests/contract/http/test_quiz_attempt_policy.py`.

### Implementation for User Story 3

- [ ] T038 [US3] Implement quiz exam configuration validation, final-attempt enforcement, and best-score projection in `app/application/use_cases/quiz_attempt_policy.py`.
- [ ] T039 [US3] Expose exam configuration and learner result-summary DTOs in `app/application/dto/quiz_attempt_policy.py` and `app/presentation/schemas/quiz_attempt_policy.py`.
- [X] T040 [US3] Add quiz configuration and canonical-result endpoints from `contracts/http.md` in `app/presentation/routers/quizzes.py`.
- [ ] T041 [US3] Run `tests/unit/domain/test_quiz_attempt_policy.py`, `tests/unit/application/test_quiz_attempt_policy.py`, `tests/integration/persistence/test_quiz_attempt_policy.py`, and `tests/contract/http/test_quiz_attempt_policy.py` and resolve only User Story 3 failures.

**Checkpoint**: Exam and non-exam attempts follow the configured product policy while final
history remains intact.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validate migration safety, direct-question compatibility, security, documentation,
and complete feature behavior.

- [ ] T042 [P] Add unsupported `DIRECT`-question start rejection and no-regression coverage in `tests/unit/application/test_quiz_sitting_use_cases.py` and `tests/contract/http/test_quiz_sittings.py`.
- [ ] T043 [P] Add structured finalization failure/redaction assertions in `tests/contract/http/test_quiz_sittings.py` and `tests/integration/persistence/test_quiz_sitting_lifecycle.py`.
- [X] T044 Update runnable validation commands, migration recovery guidance, and direct-question scope in `specs/003-enhance-quiz-sitting/quickstart.md` and `specs/003-enhance-quiz-sitting/contracts/http.md` if implementation changes contract details.
- [ ] T045 Run Alembic upgrade/check/downgrade/upgrade plus `pytest -q` in the application container; record PostgreSQL versus SQLite evidence in `specs/003-enhance-quiz-sitting/quickstart.md`.
- [X] T046 Run import-boundary review, OpenAPI route/security inspection, `compileall`, and `git diff --check`; record remaining environment limits in `specs/003-enhance-quiz-sitting/quickstart.md`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1** has no dependencies.
- **Phase 2** depends on Phase 1 and blocks all user stories.
- **US1** depends on Phase 2 and is the MVP.
- **US2** depends on Phase 2; its authoring routes share `app/presentation/routers/quizzes.py`
  with US1, so integrate it after US1 when working in one checkout.
- **US3** depends on Phase 2 and the shared finalization seam from US1.
- **Phase 6** depends on all selected user stories.

### User Story Completion Order

```text
Setup → Foundation → US1 (auditable final result) → US2 (author code management)
                                 └──────────────→ US3 (attempt policy) → Polish
```

### Parallel Opportunities

- T001–T003 can be distributed by file after agreeing on fake interfaces.
- T009 may be divided by SQLModel file after T004–T008 finalize field/value-object names.
- In each story, the explicitly marked test tasks can run in parallel because they target
  different layers.
- US2 test/design work can begin after the Foundation in parallel with US1 domain/application
  work, but its route integration must wait for US1's router seam.
- US3 domain and application tests can begin after the Foundation; its policy integration waits
  for US1 finalization.

## Parallel Examples

### User Story 1

```text
T016 tests/unit/domain/test_quiz_sitting_results.py
T017 tests/unit/application/test_quiz_sitting_use_cases.py
T018 tests/integration/persistence/test_quiz_models.py
T019 tests/contract/http/test_quiz_sittings.py
```

### User Story 2

```text
T026 tests/unit/domain/test_question_code.py
T027 tests/unit/application/test_quiz_question_codes.py
T028 tests/integration/migrations/test_quiz_sitting_backfill.py
T029 tests/contract/http/test_quiz_question_codes.py
```

### User Story 3

```text
T034 tests/unit/domain/test_quiz_attempt_policy.py
T035 tests/unit/application/test_quiz_attempt_policy.py
T036 tests/integration/persistence/test_quiz_attempt_policy.py
T037 tests/contract/http/test_quiz_attempt_policy.py
```

## Implementation Strategy

### MVP First

1. Complete Phases 1–2.
2. Complete US1 through T025.
3. Validate the final-result partition, idempotency, snapshot stability, ownership, and answer
   key redaction before beginning code-authoring or attempt-policy additions.

### Incremental Delivery

1. US1 delivers safe immutable final results for generated codes.
2. US2 adds author-managed codes and legacy data migration verification.
3. US3 adds exam limits and non-exam best-score summaries.
4. Polish validates real migration recovery, production-like concurrency, and security.
