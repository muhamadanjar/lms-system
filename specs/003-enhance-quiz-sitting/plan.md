# Implementation Plan: Enhanced Quiz Sitting Results

**Branch**: `003-enhance-quiz-sitting` | **Date**: 2026-09-28 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-enhance-quiz-sitting/spec.md`

## Summary

Extend the existing Learning Content and Assessment quiz persistence seam so every Question
has a normalized, globally unique code and every finalized Quiz Sitting has an immutable
question-and-answer snapshot, per-question outcomes, per-question scores, and a total score.
The application layer will start or resume a learner's draft, save only snapshot option
selections, and finalize atomically. Exam attempt limits are enforced transactionally;
non-exam history remains unlimited and exposes its best score as the canonical summary.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: FastAPI, Pydantic, SQLModel, SQLAlchemy, Alembic, httpx

**Storage**: PostgreSQL in deployment; SQLModel/SQLAlchemy persistence; SQLite is a focused
test fixture only

**Testing**: pytest and pytest-asyncio; domain/application fakes, persistence integration,
Alembic migration integration, and FastAPI HTTP contracts

**Target Platform**: Linux container web service

**Project Type**: Backend web service

**Performance Goals**: A learner can start, save, finalize, and retrieve a normal quiz
sitting without an additional external service; finalization performs one transactional read
and write boundary.

**Constraints**: Domain code remains framework- and ORM-free; learner responses cannot expose
answer keys; finalization is idempotent; uniqueness and exam limits must hold under concurrent
requests; schema changes require a reversible Alembic migration and legacy-question backfill.

**Scale/Scope**: One bounded context, extending Quiz, Question, Answer, QuizSitting, their
repositories/UoW, HTTP delivery, and the existing test hierarchy. This feature does not add
new learner enrollment roles, non-multiple-choice scoring, or a new external dependency.

## Constitution Check

### Pre-design gate: PASS

- **Domain-driven learning model**: Question code, answer policy, scoring, attempt policy,
  sitting finalization, and immutability are domain behavior; routers and ORM tables only
  translate and persist it.
- **Dependency direction**: Presentation calls application use cases. Application uses
  domain repository/authorization/transaction ports. SQLModel and Alembic remain in
  infrastructure.
- **Ports and package discipline**: Existing quiz repositories and UoW gain typed, focused
  ports with concrete SQLModel consumers and test fakes. No new third-party dependency is
  required.
- **Testable workflows**: The plan includes unit domain/application, persistence/migration,
  and HTTP contract coverage for every new lifecycle and failure path.
- **Security and operations**: Correct options and selected options remain server-side
  evaluation data; learner result DTOs project only code, outcome, and score. Finalization
  uses the unit-of-work transaction and errors follow the existing structured mapping.

### Post-design gate: PASS

The design keeps answer keys in protected snapshot-option rows, makes results immutable, and
uses application authorization before repository access. Every new table/port has one active
consumer. The migration has an explicit deterministic backfill and downgrade/recovery path.

## Project Structure

### Documentation (this feature)

```text
specs/003-enhance-quiz-sitting/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── http.md
└── tasks.md                 # created later by $speckit-tasks
```

### Source Code (repository root)

```text
app/
├── application/
│   ├── dto/                 # sitting commands and learner-safe result DTOs
│   ├── ports/               # authorization and typed UoW/repository contracts
│   └── use_cases/           # start/resume, save answers, finalize, query summary
├── domain/
│   ├── entities/            # Quiz, Question, QuizSitting and snapshot/result behavior
│   ├── repositories/        # Quiz, sitting, and code-allocation ports
│   ├── services/            # deterministic answer evaluation
│   └── value_objects/       # QuestionCode, AnswerPolicy, outcomes
├── infrastructure/
│   └── persistence/
│       ├── models/          # SQLModel tables for config, snapshots, selections, results
│       ├── mappers/
│       ├── repositories/
│       └── unit_of_work.py
└── presentation/
    └── routers/             # quiz authoring and learner sitting routes

alembic/versions/            # one revision extending the typed quiz content schema
tests/
├── unit/domain/
├── unit/application/
├── integration/persistence/
├── integration/migrations/
└── contract/http/
```

**Structure Decision**: Extend the existing direct `app/domain`, `app/application`,
`app/infrastructure`, and `app/presentation` layers. Do not create a second quiz context,
generic repository abstraction, or a new public API version.

## Delivery Strategy

1. Add and test pure-domain value objects, configuration, snapshot/result invariants, and
   deterministic multiple-choice evaluator.
2. Add typed ports and application commands/queries that own authorization, draft resumption,
   atomic finalization, attempt policy, and best-score projection.
3. Add SQLModel mapping/repositories and the Alembic revision: configuration fields, global
   question code/backfill allocator, snapshot options/selections/results, active-draft guard,
   and exam-attempt serialization.
4. Add the protected HTTP contract and route wiring. Preserve `/api`, Bearer authentication,
   response envelopes, and existing error translation.
5. Run domain, application, persistence, migration, and HTTP contract verification. Report
   PostgreSQL/Docker migration evidence separately from SQLite-focused tests.

## Complexity Tracking

No constitution violations require justification.
