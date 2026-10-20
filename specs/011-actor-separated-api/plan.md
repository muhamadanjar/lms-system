# Implementation Plan: Actor-Separated LMS API

**Branch**: `011-actor-separated-api` | **Date**: 2026-10-08 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/011-actor-separated-api/spec.md`

## Summary

Add canonical `/api/admin/` and `/api/learner/` route families and role-prefixed OpenAPI tags across LMS content, enrollment, assessment, task, file, lab, and server workflows. Preserve the existing application use cases, authorization decisions, request and response schemas, and persistence behavior. Keep existing routes available during migration under a deprecated `Legacy Compatibility` OpenAPI group.

## Technical Context

**Language/Version**: Python, current LMS service runtime

**Primary Dependencies**: FastAPI, Pydantic, SQLModel, SQLAlchemy, existing application use cases

**Storage**: Existing PostgreSQL persistence and configured private file storage; no schema change

**Testing**: Existing pytest unit and HTTP contract suites are the repository validation baseline; this plan does not introduce a test framework or data migration.

**Target Platform**: LMS HTTP and WebSocket service

**Project Type**: Backend API service

**Performance Goals**: No material change in request work, response size, or external-call count for existing operations.

**Constraints**: Existing API paths remain callable during the client migration. New paths must preserve behavior and authorization. API schemas and response envelopes remain unchanged. Domain policy stays in application/domain layers.

**Scale/Scope**: All actor-specific LMS operations currently defined in presentation routers, plus route ownership documentation.

## Constitution Check

- **Domain-driven model**: Pass. The change affects HTTP route ownership only; existing Course, Module, Section, quiz, enrollment, lab, and task rules remain in their existing use cases/domain objects.
- **Dependency direction**: Pass. Routers continue to call injected application use cases and existing domain/application ports; no dependency direction changes are needed.
- **Package discipline**: Pass. Use existing presentation router modules and add only active route adapters; no new runtime dependency or placeholder folder.
- **Testable workflows**: Existing HTTP contracts and authorization behavior must be preserved. The project constitution requires route regression coverage; test execution and test-file changes are outside this run's authorized verification scope and remain a release gate.
- **Security and operations**: Pass by preserving existing role/permission guards, learner ownership, publication filtering, answer-key redaction, file authorization, and server credential redaction.
- **API compatibility**: Pass with additive canonical routes and documented legacy paths. No existing path is removed in this feature.
- **Persistence**: Pass. No database migration or persisted-data change.

## Design

### Route ownership

Each existing resource router will expose actor-specific route adapters with role-specific tags. Course, Module, Section, and Quiz use cases remain the single source of business behavior. Admin routes preserve `require_content_editor`, administrative enrollment/review guards, and `servers.*` checks. Learner routes preserve current authenticated-user identity, enrollment, publication, progression, attempt ownership, and task ownership behavior.

The route split is implemented in the existing `app/presentation/routers` resource modules. Existing route handlers that combine roles remain available as compatibility operations, tagged `Legacy Compatibility` and marked deprecated in the OpenAPI schema. Compatibility handlers must call the same application use cases as canonical routes.

The OpenAPI tag list and router registration are ordered by actor: administrator groups first, learner groups second, and `Legacy Compatibility` last.

### Canonical path families

- Course, Module, and Section administration: `/api/admin/courses/...`
- Learner course discovery, published content, and progress: `/api/learner/courses/...`
- Quiz authoring and quiz-question management: `/api/admin/courses/.../quizzes/...` and `/api/admin/courses/.../sections/{section_slug}/quiz...`
- Learner quiz sitting, answer, content, finalization, and result operations: `/api/learner/courses/.../quiz/...` and `/api/learner/quiz-sittings/...`
- Administrator enrollment management: `/api/admin/enrollments` and `/api/admin/courses/{course_slug}/enrollments/...`
- Learner enrollment and own course enrollment summaries: `/api/learner/enrollments` and `/api/learner/courses/{course_slug}/enrollments/...`
- Learner task submissions and own task reads: `/api/learner/courses/.../collect-task...`
- Administrator task review: retain `/api/admin/collect-tasks...` and tag it as an Admin group.
- Learner/admin file reads: `/api/learner/files/{file_id}` and `/api/admin/files/{file_id}`, with the existing owner/admin policy.
- Learner course-lab access: `/api/learner/courses/{course_slug}/lab/...`; administrator access management: `/api/admin/courses/{course_slug}/lab/...`.
- Server inventory: `/api/admin/servers/...`; learner and administrator console WebSocket routes receive actor prefixes. The existing WebSocket route remains as a documented legacy path.

The detailed method and path mapping is in [contracts/api.http.md](contracts/api.http.md). Shared health and authentication metadata remain outside these actor namespaces.

### Compatibility and rollout

1. Add canonical routes and actor-prefixed tags without removing existing routes.
2. Mark existing paths that are replaced by canonical routes as deprecated and group their REST operations under `Legacy Compatibility`. The existing admin collect-task route is already actor-prefixed and remains canonical.
3. Update `docs/api-roles.md` with canonical paths and legacy mappings. External clients migrate separately.
4. Do not remove legacy routes automatically. A later release must inventory client usage and specify a retirement date or major-version change.

### Existing specification interaction

Specs 008 and 009 define learner progress, enrollment summary, quiz sitting content, and collect-task contracts under current prefixes. This feature supersedes those prefixes only for canonical routes. Existing paths and semantics remain available through the compatibility layer. The `sections.py` route contract stays intact during the transition; this feature does not rename Section paths to Chapter paths.

## Project Structure

### Documentation

```text
specs/011-actor-separated-api/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/api.http.md
```

### Source Code

```text
app/
├── main.py
└── presentation/
    ├── routers/
    │   ├── courses.py
    │   ├── modules.py
    │   ├── sections.py
    │   ├── quizzes.py
    │   ├── enrollments.py
    │   ├── learner_enrollments.py
    │   ├── admin_enrollments.py
    │   ├── course_labs.py
    │   ├── collect_tasks.py
    │   └── servers.py
    └── websocket/console.py

docs/api-roles.md
```

**Structure Decision**: Keep the existing direct `app/presentation/routers` layout. Resource routers own their route adapters, while application use cases continue to own orchestration and policies. `main.py` remains the composition root for all canonical and compatibility routers.

## Complexity Tracking

No constitution violations or new architectural layers are introduced.
