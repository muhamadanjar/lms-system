# Feature Specification: Course Quiz Lifecycle

**Feature Branch**: `007-quiz-section-lifecycle`
**Created**: 2026-10-01
**Status**: Draft
**Input**: Dashboard course Quiz management workflow confirmed with the operator.

## User Scenarios & Testing

### US1 — Manage Course Quizzes (P1)
As a course editor, I can create, list, edit, configure, and delete standalone quizzes owned by one Course.

Acceptance scenarios:
1. Creating a standalone Quiz sets `is_exam=false`, `max_attempts=1`, `answer_policy=SINGLE` unless explicitly provided by the trusted lifecycle contract.
2. List returns all Quiz metadata and optional Section reference scoped to the requested Course.
3. Metadata and assessment policy can be updated independently of the associated Section metadata.
4. Deleting a linked Quiz returns conflict; deleting a standalone Quiz removes it and its authored question data according to existing quiz cascade rules.

### US2 — Associate Quiz and Chapter Section (P1)
As a course editor, I can associate an unused Course Quiz with one QUIZ Section, or unlink it while preserving both records.

Acceptance scenarios:
1. Association succeeds only when Quiz and target Chapter belong to the same Course, the Chapter represents a QUIZ Section, and both are currently unassociated / unoccupied.
2. Duplicate, cross-Course, wrong-type, missing, or already-associated targets are rejected without partial persistence.
3. Unlinking clears the optional relation and preserves both Quiz and Chapter.
4. Updating the Section compatibility API from QUIZ to another type detaches its Quiz in the same transaction.
5. Deleting a Section or parent Module detaches quizzes before cascading hierarchy deletion; Course deletion retains its existing aggregate deletion semantics.

### US3 — Create Quiz with Section (P1)
When the transitional Section create API receives `content_type=QUIZ`, it creates one Quiz in the same database transaction, copying title, slug, description, status and applying defaults. Failure to create either resource rolls back both.

### US4 — Author Quiz Questions and Options (P1)
As a course editor, I can author MULTICHOICE questions, dynamically manage their options, reorder questions, and delete questions while existing sitting snapshots remain intact.

Acceptance scenarios:
1. Course-scoped list/create/update/delete/reorder endpoints require editor authorization and reject a Quiz outside the path Course.
2. Each question save atomically stores the Markdown prompt and its complete ordered option collection; incomplete drafts are allowed.
3. New attempts require a non-empty prompt, at least two options, exactly one correct option for SINGLE policy, and at least one correct option for MULTIPLE policy.
4. Reordering supplies each question exactly once with contiguous positions beginning at zero.
5. Deleting a question also deletes its options while existing sitting snapshots remain readable and scorable.
6. Authoring responses may include correct-answer flags; learner-facing responses continue to use snapshot-safe DTOs without answer keys.

## Functional Requirements

- **FR-001**: A Quiz belongs to exactly one Course and may optionally relate to one Chapter; a Chapter may have at most one Quiz.
- **FR-002**: All list, create, update, delete, associate and unlink operations are scoped to the path Course and require content-editor authorization.
- **FR-003**: Association requires a same-Course Chapter created through the compatibility `QUIZ` Section contract.
- **FR-004**: Quiz metadata is title, slug, description, status plus assessment policy (`is_exam`, `max_attempts`, `answer_policy`).
- **FR-005**: New quizzes default to false, 1, SINGLE.
- **FR-006**: Section create with `QUIZ` atomically creates a Quiz initialized from Section metadata.
- **FR-007**: Section type change, Section delete, Module delete, and explicit unlink preserve quizzes as standalone records.
- **FR-008**: A linked Quiz cannot be deleted; return HTTP 409.
- **FR-009**: Maintain existing Section routes and response shapes as compatibility adapters. New domain code uses `Chapter` and `KnowledgeQuiz` vocabulary.
- **FR-010**: Course-scoped question and option authoring is limited to MULTICHOICE and uses per-question atomic saves.
- **FR-011**: Incomplete question drafts may be stored, but new sittings enforce prompt, option-count, and AnswerPolicy correctness.
- **FR-012**: Reorder validates the full question set and persists zero-based contiguous positions.
- **FR-013**: Deleting authoring questions/options preserves historical sitting snapshots and removes no snapshot content.

## API Contract

All read and mutation responses use `{ "data": ..., "meta": {} }`; delete operations return HTTP 204.

- `GET /api/courses/{course_slug}/quizzes`
- `POST /api/courses/{course_slug}/quizzes`
- `PATCH /api/courses/{course_slug}/quizzes/{quiz_slug}`
- `DELETE /api/courses/{course_slug}/quizzes/{quiz_slug}`
- `PUT /api/courses/{course_slug}/modules/{module_slug}/sections/{section_slug}/quiz` body `{ "quiz_slug": "..." }`
- `DELETE /api/courses/{course_slug}/modules/{module_slug}/sections/{section_slug}/quiz`
- `GET /api/courses/{course_slug}/quizzes/{quiz_slug}/questions`
- `POST /api/courses/{course_slug}/quizzes/{quiz_slug}/questions`
- `PUT /api/courses/{course_slug}/quizzes/{quiz_slug}/questions/{question_slug}`
- `DELETE /api/courses/{course_slug}/quizzes/{quiz_slug}/questions/{question_slug}`
- `PUT /api/courses/{course_slug}/quizzes/{quiz_slug}/questions/order`

Question create/update bodies contain `prompt` and an ordered `options` array of `{value, is_correct}`. Updating replaces that question's full option collection in the same transaction. Authoring responses include question code, position, and option correctness; these endpoints are editor-only.

Quiz reads include `id`, `slug`, `course_id`, `title`, `description`, `status`, assessment policy, and nullable `section_id` plus nullable Section summary (`slug`, `title`, `module_slug`).

## Data Model and Migration

Quiz persistence receives a required `course_id` foreign key and nullable `section_id`; `uq_quizzes_section` remains unique and allows multiple NULL values. `section_id` uses `ON DELETE SET NULL`. Migration backfills Course ownership by joining existing Quiz → Section → Module, then makes `course_id` non-null and replaces the Section cascade FK. Questions and options remain owned by Quiz. Sitting snapshot source IDs are historical identifiers without foreign keys, so authoring deletion cannot delete or block historical snapshot data.

## Success Criteria

- **SC-001**: API enforces one Quiz per Section and one Section per Quiz under concurrent requests through database uniqueness and transactional checks.
- **SC-002**: Section/Module deletion and Section type change preserve associated Quiz rows.
- **SC-003**: Dashboard can render all Course Quiz operations from the contract above without a proxy.

## Assumptions

- Existing global slug registry remains authoritative for Quiz slug uniqueness.
- Existing Section and Module deletion semantics are otherwise unchanged.
- Course deletion can cascade the Course-owned Quiz data with the Course.
