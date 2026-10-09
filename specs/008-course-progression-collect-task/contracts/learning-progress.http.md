# Learning Progress and CollectTask HTTP Contract

Existing route prefixes and authentication conventions remain authoritative. The names below describe the required operations; implementations should extend established routers where possible.

## Course authoring

- Course create/update/read includes `progression_mode` (`FREE|SEQUENTIAL`) and `completion_mode` (`SELF_LEARNING|ADMIN_REVIEW`). Authorized content editors only.
- Section create/update/read includes `requires_pass` (boolean; default false).
- Ordinary quiz authoring includes `passing_score` (integer 0–100; default 70). Exam max-attempt configuration retains its current contract.

## Learner progress

- Section list/detail returns learner completion and access state for authenticated enrolled learners. Locked detail responses omit section body and identify the blocking section.
- `POST /courses/{course_slug}/sections/{section_slug}/complete` marks an eligible text section complete for the authenticated learner.
- Quiz sitting start checks course progression before creating or resuming a sitting. Finalized ordinary quiz results determine completion and passing; exam results do not gate this feature.

## CollectTask learner operations

- `POST /api/learner/courses/{course_slug}/modules/{module_slug}/sections/{section_slug}/collect-task/files`: multipart form with one `file`. Selecting a file uploads it immediately and commits its private object and metadata before the task submission. Return the staged `file_id`; files are scoped to the authenticated learner and section and expire after 24 hours.
- `DELETE /api/learner/courses/{course_slug}/modules/{module_slug}/sections/{section_slug}/collect-task/files/{file_id}`: discard an owned staged file that has not been attached to a submission.
- `POST /api/learner/courses/{course_slug}/modules/{module_slug}/sections/{section_slug}/collect-task/submissions`: create or revise own task with JSON `text`, optional `evidence_urls`, and optional `file_ids`. Body requires non-empty `text` and at least one HTTP(S) evidence URL or uploaded file ID. The service validates each ID against the learner and section, then attaches it to the immutable submission history in the task transaction.
- File limits: 10 files, 25 MB each, and 100 MB total per submission. Allowlist: PDF, DOCX, XLSX, PPTX, TXT, CSV, ZIP, PNG, JPG/JPEG. The multipart `/submissions/files` endpoint remains as a deprecated compatibility route.
- `GET /api/learner/courses/{course_slug}/modules/{module_slug}/sections/{section_slug}/collect-task`: read own task and history only.
- Submission history includes file metadata and private `download_url` values. `GET /api/learner/files/{file_id}` permits the task owner, `admin`, and `instructor`; all other callers are denied.
- Configure `FILE_STORAGE__BACKEND=local|s3` and `FILE_STORAGE__LOCAL_ROOT`; S3 uses `FILE_STORAGE__BUCKET`, `FILE_STORAGE__REGION`, optional `FILE_STORAGE__ENDPOINT_URL`, `FILE_STORAGE__ACCESS_KEY_ID`, and `FILE_STORAGE__SECRET_ACCESS_KEY`. Local is the default backend.
- Other learner IDs are never accepted as authority for learner operations.

## CollectTask administrator operations

- Admin queue lists submitted tasks awaiting review, without exposing credentials or quiz answer keys.
- Admin operation marks task `IN_REVIEW`.
- Admin review operation chooses `REVIEWED` or `PASSED` with score 0–100 and optional note, or `REVISION_REQUIRED` with mandatory note.
- Every decision records reviewer identity/time in immutable history.

## Enrollment completion

- Existing administrator completion operation remains available for `ADMIN_REVIEW` courses and returns a conflict/validation error while requirements are incomplete.
- `SELF_LEARNING` enrollment completes automatically once all applicable requirements are met.
- Exams are excluded from eligibility.
