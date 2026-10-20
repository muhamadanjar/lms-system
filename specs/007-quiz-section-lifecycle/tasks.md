# Tasks: Course Quiz Lifecycle

**Input**: Design documents in `specs/007-quiz-section-lifecycle/`
**Tests**: Required by LMS architecture policy; write regression coverage alongside behavior.

## Phase 1: Foundation
- [X] T001 Record current LMS worktree baseline and confirm active `.specify/feature.json` remains unchanged.
- [X] T002 Define canonical Quiz/Chapter lifecycle domain behavior and typed domain errors.
- [X] T003 Create reversible migration to add Quiz course ownership, optional unique Chapter association, and `ON DELETE SET NULL`; backfill existing rows.
- [ ] T004 Add unit tests for Quiz defaults, association rules, and metadata edits.

## Phase 2: Application and persistence
- [X] T005 Extend repository ports/implementations and mappers for Course-scoped Quiz CRUD/list/link/unlink.
- [X] T006 Implement use cases enforcing same-Course, QUIZ type, one-to-one links, linked-delete conflict, and transaction boundaries.
- [X] T007 Update Section create/update/delete and Module delete use cases to atomically create/detach quizzes.
- [ ] T008 Add unit and persistence regression tests for CRUD, concurrency constraints, detach and rollback behavior.

## Phase 3: HTTP compatibility
- [X] T009 Add request/response schemas and content-editor-only Course Quiz endpoints.
- [X] T010 Add link/unlink compatibility endpoints and keep existing quiz configuration routes working.
- [ ] T011 Add HTTP contract tests for authorization, Course isolation, defaults, validation, conflict and envelopes.

## Phase 4: Completion
- [X] T012 Update API role/endpoint documentation and migration notes.
- [ ] T013 Run focused tests, full required checks, migration upgrade/downgrade checks; record results.
- [X] T014 Re-index code graph and review diff for unrelated enrollment changes.

## Phase 3: Question authoring
- [X] T015 Add Course-scoped question list/create/update/delete and reorder routes for content editors.
- [X] T016 Save prompt and complete option set atomically; keep answer-key fields out of learner-facing routes.
- [X] T017 Validate attempt readiness using prompt, minimum option count, and Quiz AnswerPolicy.
- [X] T018 Preserve sitting snapshots when authored questions/options are deleted; add migration removing snapshot-source foreign keys.
- [ ] T019 Add regression coverage for authoring, ordering, answer policy, snapshot retention, and route authorization.

## Dependencies
T001 → T002/T003 → T005/T006 → T007 → T009/T010 → T012/T013; regression tests accompany each phase.
