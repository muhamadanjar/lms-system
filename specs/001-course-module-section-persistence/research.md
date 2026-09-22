# Research: Course Module Section Persistence

**Feature**: Course Module Section Persistence  
**Date**: 2026-09-23

## Decision 1: SQLModel Table Models Stay in Infrastructure

**Decision**: Keep domain entities and repository ports independent from SQLModel. Put SQLModel
table models, mappers, concrete repositories, and unit-of-work implementations under
`app/infrastructure/persistence`.

**Rationale**: The constitution prohibits domain imports of SQLAlchemy/SQLModel and the current
`app/domain/entities/base.py` is already coupled to SQLAlchemy, so the feature must avoid
expanding that coupling. SQLModel relationships are useful at the persistence boundary, while
domain invariants remain testable without a database.

**Evidence**: SQLModel registers `table=True` classes in `SQLModel.metadata`; the classes must
be imported before metadata is consumed. See [SQLModel table creation](https://sqlmodel.tiangolo.com/tutorial/create-db-and-table/).

**Alternatives considered**:

- Put SQLModel models in `app/domain`: rejected because it violates dependency direction.
- Use only SQLAlchemy declarative models: rejected because SQLModel is an explicit project
  constraint and already installed.

## Decision 2: Relational Hierarchy and Explicit Cascades

**Decision**: Model `Course → Module → Section` with non-null UUID foreign keys, indexes, and
unique `(parent_id, position)` constraints. Configure both ORM cascade behavior and database
foreign-key `ON DELETE CASCADE`; use `passive_deletes=True` where SQLAlchemy should delegate
deletion to the database.

**Rationale**: The feature requires deterministic ordering and atomic hard deletion. Database
constraints protect direct SQL operations, while ORM configuration keeps in-memory unit-of-work
behavior consistent. SQLite foreign keys must be enabled for integration tests.

**Evidence**: SQLModel documents relationship attributes and foreign-key relationships in its
[relationship tutorial](https://sqlmodel.tiangolo.com/tutorial/relationship-attributes/).
SQLAlchemy documents `ON DELETE CASCADE` and backend requirements in its
[constraint documentation](https://docs.sqlalchemy.org/en/20/core/constraints.html).

**Alternatives considered**:

- Application-only deletion: rejected because direct database deletes could leave descendants.
- Soft deletion: rejected because the clarification explicitly selected hard cascade.
- Unordered child lists: rejected because position is a user-visible learning order.

## Decision 3: Section as the Content Root

**Decision**: Use one `Section` table with `content_type` values `MATERIAL`, `LAB_TASK`, and
`QUIZ`. `LabEnvironmentSettings` and `Quiz` are one-to-one detail models keyed by `section_id`.

**Rationale**: This matches the clarification that Section is the primary content table while
allowing type-specific data to evolve without nullable provider or quiz columns on Section.
The application layer must reject a detail row whose Section type does not match; ordinary
SQL CHECK constraints cannot enforce a cross-table type invariant portably.

**Alternatives considered**:

- Separate top-level tables for every content type: rejected because it duplicates hierarchy,
  ordering, status, and slug behavior.
- One JSON payload on Section: rejected because relational constraints and quiz answer queries
  would become opaque.

## Decision 4: Normalized Quiz Content

**Decision**: Use `Quiz → Question → Answer` tables. Question has `MULTICHOICE` or `DIRECT` type,
position, and positive instructor-defined weight. Answer rows store option/accepted-answer
values; `is_correct` is meaningful for `MULTICHOICE`.

**Rationale**: Normalized rows support multiple options, multiple correct choices, direct-answer
matching, stable ordering, and future answer metadata without JSON parsing.

**Alternatives considered**:

- JSON options and answers: rejected because correctness constraints and queries would be weaker.
- One answer column on Question: rejected because it cannot represent multiple choices or
  accepted direct-answer variants cleanly.

## Decision 5: QuizSitting Has Content Status and Attempt State

**Decision**: `QuizSitting` receives the shared content `status` and a separate `attempt_state`
with `IN_PROGRESS`, `SUBMITTED`, `GRADED`, and `CANCELLED`. It stores a learner identity
reference without a foreign key until the identity context exists.

**Rationale**: The user requires status on every model, but publication/content status is not
enough to describe an attempt. A separate attempt state prevents semantic overloading while
preserving the shared status contract.

## Decision 6: Global Immutable Slugs

**Decision**: Each persisted content model exposes a slug, and a `content_slug_registry` table
enforces global uniqueness across model tables. Writes MUST update the model row and registry in
one unit-of-work transaction. Slugs are write-once; deleting content removes its registry row
in the same transaction, so a deleted slug may be reused by a future record.

**Rationale**: A normal unique constraint is scoped to one table and cannot enforce the
clarified global rule. The registry provides one database-enforced unique namespace without
coupling all content models through polymorphic foreign keys.

**Risk and mitigation**: Duplicated slug values can drift between the model and registry. The
repository write path MUST update both, and integration tests MUST cover duplicate creation,
immutable updates, and deletion cleanup. Direct SQL writes are outside the application contract.

## Decision 7: PostgreSQL Production, SQLite Test Smoke

**Decision**: PostgreSQL is the primary deployment database. SQLite is used only for fast unit
and migration smoke tests with foreign-key enforcement enabled. The schema avoids backend-only
types where practical and uses named constraints.

**Rationale**: The current settings default to PostgreSQL and `psycopg2` is installed. The
feature needs reliable FK cascades and transactional behavior; PostgreSQL integration tests
must cover behavior that SQLite cannot faithfully represent.

## Decision 8: Alembic Is the Schema Source of Truth

**Decision**: Add Alembic and a migration environment. `SQLModel.metadata.create_all()` remains
allowed only for isolated disposable tests; production and development schema changes use
reviewed Alembic migrations.

**Rationale**: The repository has no migration directory and `create_all()` currently sees no
LMS tables unless model modules are imported. Alembic autogenerate requires explicitly loaded
target metadata and generated migrations still require manual review.

**Evidence**: See [Alembic autogenerate](https://alembic.sqlalchemy.org/en/latest/autogenerate.html),
which requires target metadata and warns that generated revisions must be reviewed.

## Decision 9: Async Request Sessions and Sync Migration Driver

**Decision**: Use the existing async session dependency for application request paths and add
`asyncpg` for PostgreSQL runtime support. Alembic uses the existing synchronous PostgreSQL
driver. A single application unit of work owns each hierarchy mutation.

**Rationale**: The project already exposes async session dependencies and FastAPI endpoints;
adding the missing async driver completes that path. The unit of work is required for atomic
global slug registration, parent/child creation, and cascade-sensitive mutations.

**Current gap**: `app/main.py` defines but does not attach its lifespan handler. The plan
includes wiring `FastAPI(lifespan=lifespan)` as part of database integration.

## Decision 10: Secret References for Lab Credentials

**Decision**: Persist only non-secret lab metadata and opaque references such as
`password_secret_ref` and `private_key_secret_ref`. Define a `SecretResolver` application port;
only the infrastructure lab adapter resolves values at execution time.

**Rationale**: Passwords and private keys must not appear in persistence rows, domain objects,
logs, or learner responses. This preserves provider flexibility and supports a later secret
manager without changing the domain model.

## Current Repository Gaps

- No LMS SQLModel table models or migrations exist.
- No concrete repositories, mappers, or unit-of-work exist.
- The generic `IRepository` has no active consumer and will not be used as a catch-all feature
  interface; feature-specific ports will be added only with concrete consumers.
- No test directory or test runner configuration exists.
- The database manager supports sync and async engines, but async drivers are not declared.
- The existing lifespan is not attached to the FastAPI application.
