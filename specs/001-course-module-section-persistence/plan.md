# Implementation Plan: Course Module Section Persistence

**Branch**: `001-course-module-section-persistence` | **Date**: 2026-09-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-course-module-section-persistence/spec.md`

## Summary

Build the initial LMS persistence slice for Course, Module, Section, lab settings, Quiz,
Question, Answer, and QuizSitting. The design uses SQLModel table mappings in infrastructure,
framework-free domain/application ports, Alembic migrations, UUID identifiers, a shared status
enum, a global slug registry, normalized quiz answers, one-to-one Section detail models, and
transactional hard cascades. PostgreSQL is the production target; SQLite is limited to fast
test smoke coverage.

## Technical Context

**Language/Version**: Python 3.12.13 (repository runtime); code remains compatible with the
project's existing Python 3.10+ syntax where practical.

**Primary Dependencies**: FastAPI 0.141.1, SQLModel 0.0.46, SQLAlchemy 2.0.54, Pydantic 2.13.5,
pydantic-settings 2.15.0, psycopg2 2.9.13, plus Alembic, asyncpg, pytest, and pytest-asyncio
added only with implementation tasks that consume them.

**Storage**: PostgreSQL for production/integration behavior; SQLite for isolated unit and
migration smoke tests with foreign keys explicitly enabled.

**Testing**: pytest, pytest-asyncio, repository/application unit tests, PostgreSQL persistence
integration tests, migration upgrade/downgrade tests, and HTTP contract regression tests.

**Target Platform**: Linux-hosted FastAPI web service with PostgreSQL.

**Project Type**: Python web service with Clean Architecture and DDD boundaries.

**Performance Goals**: Hierarchy reads for a Course with up to 1,000 Sections complete within
500 ms p95 in the baseline integration environment; ordering and constraint operations remain
transactional rather than optimized through denormalized shortcuts.

**Constraints**: Domain code MUST remain free of SQLModel/SQLAlchemy/FastAPI/Pydantic transport
imports. Slugs are globally unique and immutable. Parent deletion is hard cascade. Raw VPS
credentials never enter persistence. Schema changes use reviewed Alembic migrations.

**Scale/Scope**: Initial persistence slice targets indexed, paginated access for up to 10,000
Courses, 100,000 Modules, and 1,000,000 Sections. Quiz content and lab settings are included
as relational extensions; lab execution, scoring, enrollment, and learner progress are not.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle/Gate | Status | Evidence in this plan |
|---|---|---|
| Domain-driven learning model | PASS | Section content types and Quiz/Lab detail ownership are explicit in `data-model.md`. |
| Clean Architecture dependency direction | PASS | SQLModel mappings stay in `app/infrastructure/persistence`; ports remain inner-layer contracts. |
| Explicit ports and package discipline | PASS | Feature-specific repositories, unit of work, and `SecretResolver` are documented; each new package has a consumer. |
| Testable workflows | PASS | `quickstart.md` defines unit, integration, migration, cascade, ordering, and secret tests. |
| Security and operational safety | PASS | Secret references only, redaction checks, named migrations, and transaction boundaries are required. |
| No unused abstractions | PASS | No generic replacement layer is added; existing generic `IRepository` is not expanded without consumers. |
| Migration and rollback | PASS | Alembic upgrade, downgrade, and `alembic check` are required. |

No constitution violations require a complexity exception.

## Project Structure

### Documentation (this feature)

```text
specs/001-course-module-section-persistence/
├── plan.md              # This file
├── research.md          # Phase 0 decisions and evidence
├── data-model.md        # Tables, relationships, constraints, and state rules
├── quickstart.md        # Runnable validation scenarios
├── contracts/
│   ├── repository-ports.md
│   └── http.md
└── tasks.md             # Phase 2 output from $speckit-tasks
```

### Source Code (repository root)

```text
app/
├── main.py                              # Attach lifespan and compose dependencies
├── config/                              # Existing settings
├── domain/
│   ├── entities/                        # Framework-free Course/Module/Section/Quiz concepts
│   ├── value_objects/                   # IDs, slugs, status, content/answer types
│   ├── services/                        # Cross-entity invariants
│   ├── repositories/                    # Feature-specific repository ports
│   └── exceptions.py                    # Domain violations
├── application/
│   ├── ports/                           # UnitOfWork, SecretResolver, identity references
│   ├── dto/                             # Persistence use-case DTOs
│   └── use_cases/                       # Hierarchy/content mutation orchestration
├── infrastructure/
│   ├── database/                        # Existing connection/session bootstrap
│   └── persistence/
│       ├── models/                      # SQLModel table mappings
│       ├── mappers/                     # SQLModel ↔ domain conversion
│       ├── repositories/                # Concrete async SQLModel repositories
│       ├── unit_of_work.py              # One async transaction per mutation
│       ├── model_registry.py            # Imports all table models for metadata
│       └── secrets/                     # SecretResolver adapter boundary
├── presentation/
│   └── routers/                         # Course, Module, and Section CRUD routers
└── core/                                # Existing cross-cutting errors/security

alembic/
├── env.py                               # Target metadata and migration engine
├── script.py.mako
└── versions/                            # Reviewed schema revisions

tests/
├── unit/domain/
├── unit/application/
├── integration/persistence/
├── integration/migrations/
└── contract/http/
```

**Structure Decision**: Use the existing `app/` layer layout without a `contexts/` directory.
The Learning Content and Assessment bounded context remains a conceptual boundary. SQLModel
models and database adapters live in `app/infrastructure/persistence`; domain/application
code does not depend on them. New directories are created only with an implementation and
consumer in the same feature.

## Phase 0 Research Summary

Research is recorded in [research.md](./research.md). Key resolved decisions are:

1. Import all SQLModel table modules through a central registry before Alembic or runtime
   metadata use.
2. Use named UUID foreign keys, `(parent_id, position)` uniqueness, and database cascades.
3. Keep Section as the content root with one-to-one LabEnvironmentSettings or Quiz detail.
4. Normalize Question answers and keep QuizSitting attempt state separate from shared content
   status.
5. Enforce global immutable slugs through a transactional registry.
6. Use async request sessions with `asyncpg`, sync migration execution with `psycopg2`, and
   secret references for VPS credentials.

## Phase 1 Design Summary

- [data-model.md](./data-model.md) defines all tables, fields, relationships, indexes,
  constraints, status rules, attempt states, and cross-table invariants.
- [contracts/repository-ports.md](./contracts/repository-ports.md) defines the repository,
  slug registry, unit-of-work, and secret resolver contracts.
- [contracts/http.md](./contracts/http.md) defines the `/api` CRUD surface, auth delegation to
  User Management `/auth/info`, pagination, ordering, and response/error contracts.
- [quickstart.md](./quickstart.md) defines migration, test, cascade, ordering, slug, status,
  quiz, and secret validation scenarios.

## Post-Design Constitution Check

| Gate | Status | Notes |
|---|---|---|
| Domain has no framework dependency | PASS | Mappings are isolated under infrastructure; mappers translate at the boundary. |
| Dependency direction points inward | PASS | Application uses ports; infrastructure implements them. |
| Every introduced abstraction has a consumer | PASS | Each port is consumed by a planned use case/repository adapter or test fake. |
| Database rules are testable | PASS | Named constraints, migrations, PostgreSQL integration, and SQLite FK smoke tests are specified. |
| Sensitive data is protected | PASS | Only secret references persist; resolver access is adapter-only. |
| Complexity is justified | PASS | Slug registry is required by global uniqueness; one-to-one detail tables avoid JSON and nullable sprawl. |

All gates pass. No complexity exception is required.

## Deferred to Implementation Planning

The following are intentionally left for task decomposition rather than additional clarification:

- Exact maximum string lengths and slug normalization library implementation.
- Exact secret manager provider and adapter configuration.
- Learner identity foreign key once the identity/auth bounded context exists.
- Detailed quiz grading algorithm and direct-answer normalization beyond persistence fields.
- Provider-specific lab provisioning behavior and network implementation.
