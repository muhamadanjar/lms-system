# Implementation Plan: Course Progression and Collect Tasks

**Branch**: `008-course-progression-collect-task` | **Date**: 2026-10-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification for course navigation, section pass policy, lab task review, and enrollment completion.

## Summary

Add course progression and completion policies, learner-specific section completion, configurable quiz pass thresholds, and a `CollectTask` review workflow. Keep domain policy in domain entities/services, orchestrate it in application use cases, persist via repositories, and expose it through existing FastAPI routers. A new migration preserves existing course behavior (`FREE` navigation, `ADMIN_REVIEW` completion).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastAPI, Pydantic, SQLModel, SQLAlchemy, Alembic
**Storage**: PostgreSQL
**Testing**: pytest; focused domain, application, persistence, and HTTP regression tests
**Target Platform**: Linux API service
**Project Type**: Backend web service
**Performance Goals**: Progression and eligibility checks should use bounded queries over one learner's course records.
**Constraints**: Do not expose quiz answer keys or another learner's submissions; maintain transitional Section API compatibility; migration IDs must fit the existing Alembic version column.
**Scale/Scope**: Course/Section authoring, learner section access and completion, quiz sitting evaluation, CollectTask lifecycle, enrollment completion.

## Constitution Check

- Domain invariants stay in pure Python domain objects/services; HTTP, ORM, and provider details remain outside domain.
- Application use cases own authorization decisions and coordinate repositories/UoW.
- Persistence changes include forward/reverse migration and persistence tests.
- Course ordering, quiz evaluation, and lab workflow changes include regression tests.
- Existing `sections.py` compatibility contract is extended without replacing its routes.

## Project Structure

```text
app/domain/entities/                 # Course and Section policy, CollectTask workflow
app/domain/services/                 # Progression and completion eligibility policy
app/domain/repositories/             # Ports for learner progress and CollectTask
app/application/use_cases/           # Authoring, section progress, task review, completion
app/infrastructure/persistence/      # SQLModel tables, mapping, repositories, UoW
app/presentation/routers/             # Existing course/section/quiz/enrollment plus task routes
app/presentation/schemas/             # Request/response schemas
alembic/versions/                     # Additive feature migration
tests/unit/ app/domain and application behavior
tests/integration/ persistence and migration behavior
tests/contract/ HTTP access and response contracts
```

**Structure Decision**: Extend active layer folders and compatibility routers; add only domain and persistence modules consumed by these use cases.

## Complexity Tracking

No constitution violations are proposed.
