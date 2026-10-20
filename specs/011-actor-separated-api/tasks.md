# Tasks: Actor-Separated LMS API

**Input**: Design documents from `specs/011-actor-separated-api/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, and `contracts/api.http.md`

**Tests**: No executable test tasks are included in this list. The project constitution's HTTP regression suite remains a release gate.

## Phase 1: Setup

- [x] T001 Reconcile the canonical and legacy route inventory in `specs/011-actor-separated-api/contracts/api.http.md` against the current router definitions before implementation.

## Phase 2: User Story 1 - Learner finds learner APIs (Priority: P1)

**Goal**: Expose learner course, content, enrollment, progress, quiz, task, file, and lab workflows under learner-prefixed paths and tags.

**Independent Test**: API documentation exposes learner groups and each learner workflow remains bound to the authenticated learner's current publication, enrollment, progression, attempt, and ownership rules.

- [x] T003 [US1] Add learner course list, detail, and progress route variants under `/api/learner/courses` in `app/presentation/routers/courses.py`.
- [x] T004 [US1] Add learner module list and detail route variants under `/api/learner/courses/{course_slug}/modules` in `app/presentation/routers/modules.py`.
- [x] T005 [US1] Add learner section list, detail, and completion route variants under `/api/learner/courses/{course_slug}/modules/{module_slug}/sections` in `app/presentation/routers/sections.py`.
- [x] T006 [US1] Add learner quiz sitting, content, answer, finalization, and result route variants under `/api/learner/` in `app/presentation/routers/quizzes.py`.
- [x] T007 [US1] Add learner self-enrollment and enrollment-summary route variants under `/api/learner/` in `app/presentation/routers/enrollments.py` and `app/presentation/routers/learner_enrollments.py`.
- [x] T008 [US1] Add learner-owned lab access and CollectTask/file route variants under `/api/learner/` in `app/presentation/routers/course_labs.py` and `app/presentation/routers/collect_tasks.py`.
- [x] T009 [US1] Add the learner console WebSocket route under `/api/learner/servers/{server_id}/console` in `app/presentation/websocket/console.py`.

## Phase 3: User Story 2 - Administrator finds administration APIs (Priority: P1)

**Goal**: Expose content authoring, quiz authoring, enrollment management, task review, lab administration, file access, and server inventory under administrator-prefixed paths and tags.

**Independent Test**: API documentation exposes administrator groups and current editor, administrator, and server permission checks remain in place.

- [x] T010 [US2] Add administrator Course, Module, and Section route variants under `/api/admin/courses` in `app/presentation/routers/courses.py`, `app/presentation/routers/modules.py`, and `app/presentation/routers/sections.py`.
- [x] T011 [US2] Add administrator quiz lifecycle, configuration, question, and section-link route variants under `/api/admin/courses` in `app/presentation/routers/quizzes.py`.
- [x] T012 [US2] Add administrator course and cross-course enrollment route variants under `/api/admin/` in `app/presentation/routers/enrollments.py` and `app/presentation/routers/admin_enrollments.py`.
- [x] T013 [US2] Add administrator lab-access, task-review, file-download, and server-inventory route variants under `/api/admin/` in `app/presentation/routers/course_labs.py`, `app/presentation/routers/collect_tasks.py`, and `app/presentation/routers/servers.py`.
- [x] T014 [US2] Add the administrator console WebSocket route under `/api/admin/servers/{server_id}/console` in `app/presentation/websocket/console.py`.
- [x] T015 [US2] Wire all canonical learner and administrator routers into the FastAPI composition root in `app/main.py` while retaining compatibility routers.

## Phase 4: User Story 3 - Existing clients migrate without interruption (Priority: P2)

**Goal**: Preserve all existing paths and contracts, while marking replaced REST paths as legacy and deprecated.

**Independent Test**: Existing requests continue to resolve and return their established status, response, and authorization behavior; API documentation lists old REST operations under `Legacy Compatibility`.

- [x] T016 [US3] Move existing routes that have canonical replacements into the `Legacy Compatibility` group and mark them deprecated in `app/presentation/routers/courses.py`, `app/presentation/routers/modules.py`, `app/presentation/routers/sections.py`, `app/presentation/routers/quizzes.py`, `app/presentation/routers/enrollments.py`, `app/presentation/routers/learner_enrollments.py`, `app/presentation/routers/admin_enrollments.py`, `app/presentation/routers/course_labs.py`, `app/presentation/routers/collect_tasks.py`, and `app/presentation/routers/servers.py`; keep the already actor-prefixed task-review routes canonical in `app/presentation/routers/collect_tasks.py`.
- [x] T017 [US3] Keep the old console WebSocket path callable and document its legacy status in `app/presentation/websocket/console.py` and `docs/api-roles.md`.
- [x] T018 [US3] Update the role matrix in `docs/api-roles.md` with canonical actor groups, path mappings, authorization notes, and the legacy route migration policy.
- [x] T019 [US3] Review canonical and legacy route registrations against `specs/011-actor-separated-api/contracts/api.http.md` and preserve the existing request, response, and status contracts in the router modules.

## Dependencies

- T001 precedes all implementation tasks.
- User Story 1 and User Story 2 modify overlapping resource modules, so their tasks are executed sequentially in listed order; T015 wires them after their handlers exist.
- User Story 3 follows both canonical route groups so each compatibility operation can be mapped to its canonical replacement.
- T016 and T017 precede T018 and T019.

## Parallel Opportunities

No implementation tasks are marked parallel: learner and administrator route work touches the same router modules and must be coordinated sequentially. Documentation review can begin after the route families are in place.

## Implementation Strategy

1. Reconcile the route contract, then add learner routes.
2. Add administrator routes to the same resource boundaries and wire them in `main.py`.
3. Tag and deprecate replaced legacy routes without removing them.
4. Update the role matrix and review the complete route mapping before client migration.
