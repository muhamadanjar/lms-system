# Tasks: Course, Module, Section, Lab, and Quiz Persistence

**Input**: Design documents from `/specs/001-course-module-section-persistence/`
**Prerequisites**: `plan.md`, `spec.md`, `data-model.md`, `contracts/repository-ports.md`, `quickstart.md`

## Execution Rules

- Every task is independently checkable and names the primary file or directory it changes.
- `[P]` means the task can run in parallel with other tasks in the same phase because it has no unfinished dependency on their files.
- User-story tasks are tagged with `[US1]`, `[US2]`, or `[US3]`.
- Domain code remains framework-free; SQLModel, SQLAlchemy, Alembic, and database concerns stay under infrastructure.
- Complete foundational tasks before starting user-story implementation tasks.

## Phase 1: Setup

**Purpose**: Prepare dependencies, migration tooling, and test execution for the persistence feature.

- [X] T001 Add Alembic, asyncpg, pytest, and pytest-asyncio with compatible versions to `requirements.txt`, preserving the existing FastAPI/SQLModel dependency set.
- [X] T002 Create migration configuration in `alembic.ini` and the migration template in `alembic/script.py.mako` using the repository database configuration conventions.
- [X] T003 [P] Create pytest configuration in `pytest.ini` with asyncio mode, unit/integration markers, and the project import path.
- [X] T004 [P] Create the feature test directory structure under `tests/unit/domain/`, `tests/unit/application/`, `tests/integration/persistence/`, `tests/integration/migrations/`, and `tests/contract/http/`.

## Phase 2: Foundational Architecture

**Purpose**: Establish shared domain contracts, persistence metadata, transaction boundaries, and test fixtures required by all user stories.

- [X] T005 Refactor `app/domain/entities/base.py` so shared entity behavior is framework-free and no longer imports SQLAlchemy, while preserving the domain entity contract used by the application.
- [X] T006 Create domain value objects and enums in `app/domain/value_objects/content.py` for `ContentStatus`, `SectionContentType`, `QuestionType`, `AccessMethod`, and `QuizAttemptState` with normalization and validation rules.
- [X] T007 Define content repository ports in `app/domain/repositories/content.py` for Course, Module, Section, slug registry, and the unit-of-work boundary using `abc.ABC` or `typing.Protocol`.
- [X] T008 Define application ports in `app/application/ports/unit_of_work.py` and `app/application/ports/secrets.py` for transaction coordination and `SecretResolver`, including the rule that raw credentials never cross into persistence.
- [X] T009 Create SQLModel shared table mixins in `app/infrastructure/persistence/models/base.py` for UUID identity, immutable slug, status, timestamps, and common indexes.
- [X] T010 Create the SQLModel metadata registry in `app/infrastructure/persistence/model_registry.py` and import every persistence model from one explicit registry used by Alembic and tests.
- [X] T011 Update `app/config/database.py` and `app/infrastructure/database/connection.py` to support PostgreSQL async request sessions, synchronous Alembic connections, SQLite foreign-key enforcement for smoke tests, and safe session cleanup.
- [X] T012 Create Alembic environment wiring in `alembic/env.py` that loads the application settings, imports `app/infrastructure/persistence/model_registry.py`, and supports online PostgreSQL migrations without falling back to `create_all`.
- [X] T013 Create reusable database fixtures in `tests/conftest.py` for isolated SQLite smoke tests and PostgreSQL integration tests, including transaction rollback and test secret resolver fixtures.
- [X] T014 [P] Add metadata and migration smoke tests in `tests/integration/migrations/test_model_registry.py` to prove all registered models are loaded and Alembic does not report an empty metadata set.
- [X] T015 [P] Attach the existing lifespan to the FastAPI instance in `app/main.py` and add a startup/shutdown smoke test in `tests/integration/test_lifespan.py` without opening a production database connection during import.

**Checkpoint**: The application can import domain and persistence layers independently, Alembic can load the model registry, and tests can create isolated database sessions.

## Phase 3: User Story 1 - Create and Load the Course Hierarchy (Priority: P1)

**Goal**: Persist and retrieve Course → Module → Section with non-null relationships and stable slugs.

**Independent test**: Create one course with ordered modules and sections, reload it through the application port, and verify the complete hierarchy and order.

- [X] T016 [P] [US1] Write framework-free hierarchy behavior tests in `tests/unit/domain/test_content_hierarchy.py` for required titles, immutable slugs, valid parent references, and non-negative positions.
- [X] T017 [P] [US1] Write hierarchy repository integration tests in `tests/integration/persistence/test_content_hierarchy.py` for create, load-by-id, load-by-slug, and deterministic nested ordering.
- [X] T018 [P] [US1] Define the pure domain entities in `app/domain/entities/course.py`, `app/domain/entities/module.py`, and `app/domain/entities/section.py` with explicit constructors and invariant validation.
- [X] T019 [P] [US1] Define SQLModel tables in `app/infrastructure/persistence/models/course.py`, `app/infrastructure/persistence/models/module.py`, and `app/infrastructure/persistence/models/section.py` with UUID foreign keys, non-null parent relationships, status, slug, timestamps, and `(parent_id, position)` uniqueness.
- [X] T020 [US1] Define the global slug registry table in `app/infrastructure/persistence/models/content_slug_registry.py` and include it in `app/infrastructure/persistence/model_registry.py` for transactionally enforced global slug uniqueness.
- [X] T021 [US1] Create the initial hierarchy migration in `alembic/versions/0001_initial_content_hierarchy.py` for courses, modules, sections, and `content_slug_registry`, including PostgreSQL UUIDs, indexes, constraints, and foreign-key cascade rules.
- [X] T022 [US1] Implement SQLModel-to-domain mappers in `app/infrastructure/persistence/mappers/content_mapper.py` and repository adapters in `app/infrastructure/persistence/repositories/course_repository.py`, `app/infrastructure/persistence/repositories/module_repository.py`, and `app/infrastructure/persistence/repositories/section_repository.py`.
- [X] T023 [US1] Implement the transaction boundary in `app/infrastructure/persistence/unit_of_work.py` and connect it to the content repository ports with one async commit/rollback lifecycle.
- [X] T024 [US1] Implement hierarchy application use cases in `app/application/use_cases/content_hierarchy.py` for creating a course aggregate, adding modules/sections, and loading a complete hierarchy without exposing SQLModel types.
- [X] T025 [US1] Run the hierarchy unit and integration tests and document the successful create/load scenario in `specs/001-course-module-section-persistence/quickstart.md`.

**Checkpoint**: US1 is independently usable; callers can create and read a complete ordered Course → Module → Section aggregate through application ports.

## Phase 4: User Story 2 - Maintain Ordering and Relationships (Priority: P1)

**Goal**: Safely reorder content, preserve deterministic order, and delete a course aggregate atomically with hard cascades.

**Independent test**: Reorder modules and sections, verify persisted positions, then delete the course and verify all descendants and slug reservations are removed.

- [X] T026 [P] [US2] Write ordering and cascade integration tests in `tests/integration/persistence/test_ordering_and_cascade.py` for module reorder, section reorder, hard course delete, and removal of slug registry rows.
- [X] T027 [P] [US2] Write concurrent position-conflict tests in `tests/integration/persistence/test_concurrent_ordering.py` for duplicate sibling positions and transaction rollback on uniqueness failure.
- [X] T028 [US2] Add ordering and relationship methods to `app/domain/entities/module.py`, `app/domain/entities/section.py`, and `app/domain/services/content_ordering.py`, including contiguous-position validation where the use case requires it.
- [X] T029 [US2] Implement atomic reorder, delete, and cascade-safe repository operations in `app/infrastructure/persistence/repositories/module_repository.py`, `app/infrastructure/persistence/repositories/section_repository.py`, `app/infrastructure/persistence/repositories/course_repository.py`, and `app/infrastructure/persistence/unit_of_work.py`.
- [X] T030 [US2] Complete database-level cascade and sibling-position constraints in `alembic/versions/0001_initial_content_hierarchy.py`, including `ON DELETE CASCADE` on all hierarchy and slug-registry foreign keys.
- [X] T031 [US2] Add reorder and aggregate-delete use cases to `app/application/use_cases/content_hierarchy.py`, ensuring one unit-of-work controls all affected rows.
- [X] T032 [US2] Add ordering and cascade contract coverage to `tests/integration/persistence/test_repository_contracts.py` and verify PostgreSQL behavior through the quickstart test commands in `specs/001-course-module-section-persistence/quickstart.md`.

**Checkpoint**: US1 and US2 together provide a reliable ordered hierarchy with atomic relationship maintenance and hard deletion semantics.

## Phase 5: User Story 3 - Manage Status, Lab Tasks, Quizzes, and Sittings (Priority: P2)

**Goal**: Persist typed section content, lab/VPS settings, normalized quiz questions and answers, quiz sittings, statuses, timestamps, and globally unique slugs.

**Independent test**: Create each section type, validate its one-to-one child aggregate, persist only secret references for lab access, store both question types and answers, create a quiz sitting, and verify invalid cross-type combinations fail.

- [X] T033 [P] [US3] Write status and slug integration tests in `tests/integration/persistence/test_status_and_slugs.py` for shared statuses, immutable slugs, global uniqueness, timestamp updates, and release after hard delete.
- [X] T034 [P] [US3] Write lab settings integration tests in `tests/integration/persistence/test_lab_environment_settings.py` for password/public-key access modes, secret references, one-to-one ownership, and rejection of raw passwords/private keys.
- [X] T035 [P] [US3] Write quiz persistence integration tests in `tests/integration/persistence/test_quiz_models.py` for quiz ownership, weighted MULTICHOICE and DIRECT questions, normalized answers, and QuizSitting lifecycle states.
- [X] T036 [P] [US3] Write section type invariant tests in `tests/integration/persistence/test_section_content_types.py` for exactly one matching LabEnvironmentSettings or Quiz child and rejection of mismatched child records.
- [X] T037 [P] [US3] Define pure domain entities in `app/domain/entities/lab_environment.py`, `app/domain/entities/quiz.py`, `app/domain/entities/question.py`, `app/domain/entities/answer.py`, and `app/domain/entities/quiz_sitting.py` with validation for access methods, question types, weights, accepted answers, and attempt states.
- [X] T038 [P] [US3] Define SQLModel tables in `app/infrastructure/persistence/models/lab_environment_settings.py`, `app/infrastructure/persistence/models/quiz.py`, `app/infrastructure/persistence/models/question.py`, `app/infrastructure/persistence/models/answer.py`, and `app/infrastructure/persistence/models/quiz_sitting.py` with one-to-one, one-to-many, cascade, enum, and index constraints.
- [X] T039 [US3] Add typed content models and the global slug registry imports to `app/infrastructure/persistence/model_registry.py`, including the invariant that only LAB_TASK sections own lab settings and only QUIZ sections own quizzes.
- [X] T040 [US3] Create the typed-content migration in `alembic/versions/0002_typed_section_content.py` for lab settings, quizzes, questions, answers, and quiz sittings, including unique one-to-one keys, cascade rules, secret-reference columns, and learner identity references.
- [X] T041 [US3] Implement typed-content mappers in `app/infrastructure/persistence/mappers/typed_content_mapper.py` for Section, LabEnvironmentSettings, Quiz, Question, Answer, and QuizSitting without leaking persistence models into the domain.
- [X] T042 [US3] Implement typed-content repositories in `app/infrastructure/persistence/repositories/lab_environment_repository.py`, `app/infrastructure/persistence/repositories/quiz_repository.py`, `app/infrastructure/persistence/repositories/quiz_sitting_repository.py`, and `app/infrastructure/persistence/repositories/content_slug_repository.py`.
- [X] T043 [US3] Implement the secret resolver adapter and test double in `app/infrastructure/secrets/secret_resolver.py` and `tests/unit/application/test_secret_resolver.py`, ensuring only opaque secret references are persisted.
- [X] T044 [US3] Add content policy validation in `app/domain/services/content_policy.py` and status/slug application use cases in `app/application/use_cases/content_management.py` for immutable global slugs, allowed transitions, section-type ownership, and timestamp behavior.
- [X] T045 [US3] Add quiz and lab application use cases in `app/application/use_cases/quiz_management.py` and `app/application/use_cases/lab_management.py` for normalized answer management, instructor weights, QuizSitting creation/submission/grading state, and secret resolution at execution time.
- [X] T046 [US3] Run all US3 tests and update `specs/001-course-module-section-persistence/quickstart.md` with lab secret-reference, quiz answer, QuizSitting, status, and invalid cross-type validation scenarios.

**Checkpoint**: All specified content types are persisted through typed aggregates while preserving security, ownership, status, slug, and quiz-answer invariants.

## Phase 6: Final Verification and Polish

**Purpose**: Verify the complete feature against the specification and keep project documentation and tooling consistent.

- [X] T047 [P] Add migration upgrade/downgrade and schema drift tests in `tests/integration/migrations/test_migrations.py` covering `alembic upgrade head`, `alembic downgrade -1`, and `alembic check`.
- [X] T048 [P] Add application-layer port boundary tests in `tests/unit/application/test_use_case_boundaries.py` proving use cases do not depend on SQLModel sessions or infrastructure model classes.
- [X] T049 [P] Add security regression tests in `tests/integration/persistence/test_secret_redaction.py` proving passwords, private keys, and resolved secret values do not appear in persisted rows, DTOs, or log records.
- [X] T050 Review `app/`, `alembic/`, and `tests/` for unused files and imports, remove only feature-created dead code, and update `AGENTS.md` if the implemented layout or mandatory conventions changed.
- [X] T051 Run the complete validation commands from `specs/001-course-module-section-persistence/quickstart.md`, including unit tests, PostgreSQL integration tests, migration checks, and the project formatter/linter/type checker; record any environment-specific skips in the quickstart document.

## Dependencies and Execution Order

### Phase Dependencies

1. **Phase 1 - Setup**: no prerequisites.
2. **Phase 2 - Foundational**: depends on Phase 1; blocks all user stories.
3. **Phase 3 - US1**: depends on Phase 2 and creates the base hierarchy.
4. **Phase 4 - US2**: depends on US1 persistence models, repositories, and unit of work.
5. **Phase 5 - US3**: depends on US1 Section and slug infrastructure; it can begin after the base hierarchy is available, but its migration must follow `0001`.
6. **Phase 6 - Final Verification**: depends on all required user-story tasks.

### User Story Dependencies

- **US1** is the MVP and can be delivered independently after Phase 2.
- **US2** requires US1's Course, Module, Section tables and transaction boundary.
- **US3** requires US1's Section table, common content fields, slug registry, model registry, and unit of work; it does not require US2's reorder use cases.

### Parallel Opportunities

- After Phase 1, T003 and T004 can run in parallel with T002.
- In Phase 2, T014 and T015 can run in parallel after the model registry and database configuration tasks they exercise are available.
- In US1, T016, T017, T018, and T019 can be developed in parallel before repository wiring is integrated.
- In US2, T026 and T027 can be developed in parallel with T028, provided they target the established US1 schema.
- In US3, T033 through T038 can be developed in parallel because they cover separate test suites and domain/model files.
- In final verification, T047, T048, and T049 can run in parallel.

## MVP Scope

The recommended MVP is Phase 1, Phase 2, and all of Phase 3 (T001-T025). It delivers a clean-architecture persistence slice for Course → Module → Section with immutable globally unique slugs, statuses, deterministic ordering, migrations, repositories, use cases, and integration tests. Phase 4 adds production-safe ordering and deletion behavior; Phase 5 adds lab and quiz capabilities.

## Phase 7: HTTP CRUD Extension

**Purpose**: Expose the confirmed `/api` Course, Module, and Section CRUD surface with delegated
User Management authentication.

- [X] T052 Add User Management settings and `/auth/info` auth adapter in `app/config/usermanagement.py`, `app/application/ports/auth.py`, and `app/infrastructure/auth/usermanagement_client.py`.
- [X] T053 Add FastAPI auth dependencies and role enforcement in `app/presentation/dependencies/auth.py` for `admin`, `instructor`, and published learner reads.
- [X] T054 Add CRUD DTOs, pagination, ordering payloads, response envelopes, and error payloads in `app/presentation/schemas/content.py` and `app/presentation/exception_handlers.py`.
- [X] T055 Implement Course, Module, and Section CRUD plus atomic reorder routers in `app/presentation/routers/courses.py`, `app/presentation/routers/modules.py`, and `app/presentation/routers/sections.py`, composed by `app/main.py`.
- [X] T056 Add HTTP contract coverage in `tests/contract/http/test_content_crud.py` and verify the generated OpenAPI route set includes every CRUD and reorder endpoint.
- [X] T057 Document the `/api` route contract and User Management integration in `specs/001-course-module-section-persistence/contracts/http.md` and `specs/001-course-module-section-persistence/quickstart.md`.
