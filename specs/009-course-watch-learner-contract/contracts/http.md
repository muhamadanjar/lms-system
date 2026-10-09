# HTTP Contract

## Course Watch learner progress

`GET /api/learner/courses/{course_slug}/progress` returns Course state, ordered
Section states, and `last_opened` (either `null` or an object with `module_slug`
and `section_slug`). Section states include `is_accessible`, `is_complete`,
`requires_pass`, and `state`. The `last_opened` position belongs to the
authenticated learner's Enrollment.

`PUT /api/learner/courses/{course_slug}/progress/position` accepts `module_slug`
and `section_slug`. It records a published Section only when the authenticated
learner has an `ENROLLED` or `COMPLETED` Enrollment and the Section is currently
accessible under the Course progression policy. The response returns the saved
`module_slug` and `section_slug`.

Legacy unprefixed Course Watch routes remain deprecated compatibility routes;
resume-position writes are available only on the learner route.

## GET /api/courses/{course_slug}/progress

Authenticated learner response contains Course state and ordered Section states.
Each section includes `module_slug`, `section_slug`, `content_type`,
`is_accessible`, `is_complete`, `requires_pass`, and `state`. Course state is one of `IN_PROGRESS`,
`ELIGIBLE_FOR_COMPLETION`, `PENDING_ADMIN_REVIEW`, or `COMPLETED`.

## GET /api/me/enrollments

Authenticated learner response returns only `ENROLLED` and `COMPLETED` Course
enrollments. Every item contains `course` (`slug`, `title`, `description`),
`enrollment` (`status`, `enrolled_at`, `completed_at`), and `progress`
(`completed_sections`, `total_sections`, `percentage`, `course_state`). Section
counts include only published Sections. Withdrawn records and data belonging to
other users are excluded.

## GET /api/courses/{course_slug}/modules/{module_slug}/sections/{section_slug}/quiz/result

The learner result summary contains `best_score`, `best_percentage`,
`is_passed`, and attempt counts. Practice clients may render per-question
outcomes from `result`; exam clients must render only the aggregate fields and
attempt availability. Exam final and result responses return empty
question-feedback collections.

## GET /api/quiz-sittings/{sitting_id}/content

Authenticated sitting owner response contains the immutable sitting snapshot:
`question_code`, `prompt`, `answer_policy`, `position`, options with `id`,
`value`, and `position`, plus that question own `selected_option_ids`.
`is_correct`, correct option IDs, and another learner selections are excluded.

## CollectTask

`GET` and `POST` at the section `collect-task` resource return the learner's
own submission status, review note, score, evidence history, and file metadata.
The multipart submission route accepts a text description, repeated evidence
URLs, and optional files; the learner must submit text and at least one URL or
file.
