# `mark_text_complete` accepts a COMPLETED enrollment

Related: learner Course Watch navigation (dashboard `features/modules/lms/courses`).

## Problem

Learners whose course already finished (`EnrollmentStatus.COMPLETED`) could browse
sections and save their watch position, but every `POST /api/learner/courses/{course}/modules/{module}/sections/{section}/complete`
returned `403 active course enrollment is required`.

- `course_progress` and `record_position` authorize on `list_history(...)[0].status in {ENROLLED, COMPLETED}`
- `mark_text_complete` used `enrollments.get_live(...)` which only matches `ENROLLED` (`EnrollmentStatus.LIVE`)

A learner finishing a Course therefore stopped being able to mark text material complete
(`Selanjutnya` in Course Watch), with no useful error in the UI.

## Change

`app/application/use_cases/learner_progress.py` — `mark_text_complete` now uses the same
history-based check as `record_position`. `WITHDRAWN` / missing enrollment still raises 403.

## Test

`tests/contract/http/test_learning_progress.py::test_completed_learner_can_still_complete_text_material`
— COMPLETED enrollment can complete text material and sees `is_complete: true` in progress.
Fails with 403 on the old `get_live` check.
