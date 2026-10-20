# Data Model: Course Progression and Collect Tasks

## Course policy

- `progression_mode`: `FREE | SEQUENTIAL`; default `FREE` for all rows.
- `completion_mode`: `SELF_LEARNING | ADMIN_REVIEW`; existing rows migrate to `ADMIN_REVIEW`, new rows default `SELF_LEARNING`.

## Section policy

- `requires_pass`: boolean, default false.
- For ordinary quiz sections, the quiz owns a configurable `passing_score` from 0 to 100, default 70.
- Exam sections ignore `requires_pass` for navigation and course completion.

## SectionCompletion

- One row per `(learner_id, section_id)`; unique constraint prevents duplicate completion.
- Stores completion state and completion timestamp. Only text materials use this record.

## CollectTask

- One current workflow per `(learner_id, section_id)`; section must be a lab section and learner must be enrolled in its course.
- Stores current status (`SUBMITTED`, `IN_REVIEW`, `REVISION_REQUIRED`, `REVIEWED`, `PASSED`), latest score/review note and timestamps.
- Each submission and review is an append-only history item with actor, action/status, text, evidence URLs, uploaded files, optional score/note, and timestamp. Submission payloads are immutable.
- Valid transitions: initial submit → `SUBMITTED`; `SUBMITTED` → `IN_REVIEW`; `IN_REVIEW` → `REVISION_REQUIRED`, `REVIEWED`, or `PASSED`; `REVISION_REQUIRED` → `SUBMITTED`.
- Score is an integer in [0,100]; revision requires a non-empty note; pass note is optional.

## Files and CollectTask M2M

- `files` stores file metadata only: original filename, canonical MIME type, size, SHA-256, uploader, backend, private storage key, optional upload section scope, optional staged-upload expiry, and creation timestamp.
- A selected file is stored as a staged row before the task transaction. Only the uploader can attach it, and only to the scoped section within 24 hours; one file ID can be attached to one submission event.
- Unattached staged rows and their private objects are deleted after expiry. Learners can discard staged files before submission.
- Object bytes are stored through `local` or S3-compatible storage. `local` is the development default; production selects `s3` through environment configuration.
- `collect_task_files` is the M2M association between `CollectTask`, `Files`, and the exact `collect_task_history` submission event. The history reference preserves files from earlier revisions.
- Allowed formats are PDF, DOCX, XLSX, PPTX, TXT, CSV, ZIP, PNG, JPG, and JPEG. Limits are 10 files, 25 MB per file, and 100 MB per submission.
- File reads require the task owner, `admin`, or `instructor`; file object keys are never returned by the API.

## Completion eligibility

- Text: `SectionCompletion` exists.
- Ordinary quiz: finalized sitting exists; if section requires pass, result percentage meets the quiz threshold.
- Lab: latest task has an admin review without revision request (`REVIEWED` or `PASSED`); if section requires pass, current status is `PASSED`.
- Exam: excluded.
- Self-learning mode automatically transitions eligible enrollment to `COMPLETED`. Admin-review mode allows the authorized administrator completion action only after the same eligibility policy returns eligible.

## Migration/backfill

- Add Course and Section policy columns with backward-compatible defaults.
- Backfill existing Courses to `ADMIN_REVIEW`; new Course creation uses `SELF_LEARNING` when omitted.
- Create learner completion, task, and task history tables with foreign keys and uniqueness constraints.
- Add quiz passing threshold with server-side default 70.
- Downgrade drops only feature-owned tables/columns.
