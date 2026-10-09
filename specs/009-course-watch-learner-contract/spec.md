# Feature Specification: Course Watch Learner Contract

**Feature Branch**: `009-course-watch-learner-contract`

## Objective

Provide learner-safe LMS contracts required by Dashboard Course Watch and the
learner Course library: a Course progress summary, a learner enrollment-summary
list, and a Quiz Sitting content payload. Extend existing learner completion,
Quiz Sitting, and CollectTask workflows without exposing answer keys.

## Requirements

- `GET /api/courses/{course_slug}/progress` returns the caller own Enrollment
  state, Course completion state, and one ordered entry per published Section.
- Section states are `LOCKED`, `AVAILABLE`, `COMPLETED`, `IN_PROGRESS`,
  `PASSED`, `FAILED`, `ATTEMPTS_EXHAUSTED`, `SUBMITTED`, `IN_REVIEW`,
  `REVISION_REQUIRED`, and `REVIEWED`, applied only where the Section type
  permits them.
- The summary identifies `is_accessible`, `is_complete`, `requires_pass`, and
  an optional blocking Section; it never includes another learner data.
- `GET /api/quiz-sittings/{sitting_id}/content` returns only the owner sitting
  snapshot: ordered prompt, answer policy, option ID/value/position, and saved
  option IDs. It excludes correctness, answer keys, and other learner answers.
- Existing start, save, finalize, and result endpoints retain their attempt
  lifecycle; exam final and result responses redact per-question feedback.
- Course progress is derived by application use cases from existing completion,
  Quiz result, CollectTask, and Enrollment records. No new persistence entity is
  introduced.
- `GET /api/me/enrollments` returns only the caller's `ENROLLED` and
  `COMPLETED` Courses. Each record includes the Course identity, Enrollment
  timestamps, Course state, and a summary of completed versus total published
  Sections. Withdrawn history and another learner's data are excluded.

## Acceptance scenarios

1. A learner in a sequential Course receives locked later Sections and their
   first blocking Section from one progress response.
2. A material completion, Quiz finalization, or Lab task submission changes the
   following progress response without client-side inference.
3. A learner can read only their own sitting snapshot and never receives
   `is_correct` or correct option IDs.
4. A finalized practice result may identify outcomes by question; an exam result
   response remains aggregate-only.
5. Self-learning and admin-review Course completion states remain distinct.
6. A learner's Course library receives one aggregate response without inferring
   progress from unpublished content or querying another learner's enrollment.
