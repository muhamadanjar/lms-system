# Research: Course Progression and Collect Tasks

## Existing LMS Behavior

- `Course` and `Section` are the persistence names used by the transitional content API. Domain vocabulary remains `Course`, `Module`, and `Section` in current code, while the repository guidance uses `Chapter` as the canonical target term.
- Course and Section CRUD already use editor-only routes and expose typed Pydantic schemas. Course update forwards only fields explicitly present in the request.
- Learner section list/detail routes currently return published Section content without learner-specific completion state or progression checks.
- Quiz sitting start is path-scoped through Course → Module → Section → Quiz and is the proper application boundary for quiz access enforcement.
- Quiz final results preserve the total number of correct questions and the available question codes. A percentage score can be calculated from these persisted values without exposing answer keys.
- Enrollment completion currently has an editor-only endpoint. The new Course completion setting will retain that path for admin-reviewed courses and provide learner completion behavior for self-learning courses.
- `SqlModelUnitOfWork` wires the active repositories; the new learner progress and task repositories must be added there and exposed through application-owned ports.
- Authorization dependencies support role and permission checks, including superuser bypass. Task review endpoints must use the existing administrator/content-review authorization conventions.

## Decisions

- Course navigation mode is `FREE` or `SEQUENTIAL`; both existing and new courses default to `FREE`.
- Course completion mode supports self-learning automatic completion and admin review followed by an administrator completion action. Existing Courses default to `ADMIN_REVIEW`; newly created Courses default to `SELF_LEARNING`.
- `Section.requires_pass` applies to ordinary quizzes and lab tasks and defaults to `false`; exams are excluded.
- Required ordinary quizzes may be retried until passed. Existing `max_attempts` remains scoped to exams.
- A lab never blocks access to the next Section. Its submission must be reviewed without a revision request to satisfy course completion (`REVIEWED` or `PASSED`); `requires_pass=true` additionally requires `PASSED`.
- CollectTask retains the latest workflow state and immutable submission/review history. Each learner submission requires both written work and one or more HTTP(S) links.
- Admin task scores are integers from 0 to 100; `REVISION_REQUIRED` requires a review note.

## Remaining Design Detail

- Ordinary KnowledgeQuiz passing threshold defaults to 70/100 and is editor-configurable. Store the threshold with quiz assessment configuration and calculate percentage from final sitting results.
- For `ADMIN_REVIEW`, retain the current administrator completion operation but reject it while required work remains incomplete. For `SELF_LEARNING`, complete the enrollment automatically after the same eligibility criteria are met.

## Alternatives Considered

- Applying a Course pass requirement to exams was rejected because the user explicitly excludes exam progression/completion from this feature.
- Blocking next Section access on lab review was rejected; learners can proceed while lab review continues.
- Storing only the latest CollectTask payload was rejected because learner resubmission and admin review history must be retained.
- Allowing free navigation to bypass a required pass was accepted only for access in `FREE`; the pass remains part of completion eligibility.
