# Implementation Plan: Course Quiz Lifecycle

## Summary
Extend canonical LMS learning content persistence so Quiz records are Course-owned and optionally associated with a Chapter, while preserving the transitional `/sections` API contract used by Dashboard.

## Decisions
- Domain names: `Chapter` and `KnowledgeQuiz`; compatibility transport continues to use Section/QUIZ.
- Database invariants: non-null Quiz course FK, nullable unique section/chapter FK, delete-set-null from Chapter.
- Application owns lifecycle orchestration and transaction boundaries. Domain entity owns metadata validation and assessment defaults.
- Section/Module deletion and type conversion explicitly detach Quiz before deleting/converting Chapters.
- Quiz create/list/update/delete and link/unlink all require content-editor authorization and Course scoping.

## Workstreams
1. **Persistence**: reversible Alembic migration, Quiz ORM ownership/relation, mapper/repository queries and uniqueness handling.
2. **Domain/application**: Quiz entity supports Course ownership and optional Chapter association; use cases for lifecycle, atomic section creation, detachment, and Course-scoped checks.
3. **Presentation**: typed request/response schemas and REST operations under `/api/courses/{course_slug}`; retain current section paths.
4. **Compatibility lifecycle**: section create creates Quiz transactionally; section type change/delete and module delete detach Quiz records.
5. **Question authoring**: course-scoped authoring use cases, transactional question/option saves, full-set reorder, author-only answer-key responses, and attempt readiness validation.
6. **Verification/docs**: unit/domain tests, persistence and HTTP contract tests, migration upgrade/downgrade review, API documentation.

## Risks
- Existing question/sitting persistence depends on Quiz identity; migration must preserve all quiz and question rows.
- Quiz slugs share the global content slug registry; standalone Quiz creation must reserve/release consistently.
- Transitional compatibility code must remain stable while mapping to canonical domain terminology.
- Sitting snapshots must outlive Question and Option rows; their source IDs are retained as historical values rather than restrictive foreign keys.

## Rollback
Downgrade restores required Section FK only after confirming no standalone Quiz rows remain. Since application-created standalone records make a downgrade lossy, downgrade must fail clearly when such rows exist rather than deleting Quiz data.
