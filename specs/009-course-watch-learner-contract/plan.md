# Implementation Plan: Course Watch Learner Contract

Extend active `LearnerProgressUseCases`, `EnrollmentUseCases`, and
`QuizSittingUseCases` with read DTOs.
Keep progression, ownership, passing, and completion logic in application/domain
layers. Presentation schemas map DTOs to `{data, meta}` responses. The feature is
mostly read-oriented at persistence level. Learner resume position is stored on the Enrollment and requires an additive migration.

## Changes

1. Add typed learner progress DTOs and application summary queries, including
   the authenticated learner's eligible Course list.
2. Add a learner-safe Quiz Sitting content DTO built from existing immutable
   snapshots and current saved selections.
3. Add Pydantic schemas and HTTP routes in existing course/quiz routers.
4. Add HTTP and application regression tests for ownership, locks, status
   mapping, and answer-key redaction.
5. Persist the last opened published, accessible Section per Enrollment and expose learner-only read/write progress-position contracts.
6. Add a nullable Enrollment-to-Section migration and HTTP/persistence regression coverage.
7. Update Dashboard Course Watch API/types and resume the saved Section.
