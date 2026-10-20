# Feature Specification: Course Progression and Collect Tasks

**Feature Branch**: `008-course-progression-collect-task`

**Created**: 2026-10-02

**Status**: Draft

**Input**: Course setting to allow free navigation or sequential learning, section-level pass requirements, and learner task submission/review for labs.

## User Scenarios & Testing

### User Story 1 - Configure Course Progression (Priority: P1)

As a course editor, I can choose whether learners may open course sections freely or must progress in order, and set whether ordinary quizzes and labs require a pass.

**Why this priority**: The authoring policy defines how learner access and completion must behave.

**Independent Test**: Create and update a course and its sections, then confirm the persisted settings and learner access behavior.

**Acceptance Scenarios**:

1. **Given** an existing or newly created course, **When** no progression mode is provided, **Then** its mode is `FREE`.
2. **Given** an editor changes the course mode, **When** the course is read, **Then** the selected `FREE` or `SEQUENTIAL` mode is returned.
3. **Given** an editor creates or updates a section, **When** `requires_pass` is omitted, **Then** it defaults to `false`; when provided, the setting applies to ordinary knowledge quizzes and lab tasks.
4. **Given** a quiz is configured as an exam, **When** section pass requirements are evaluated, **Then** the exam remains outside this feature's progression and course-completion rules.

### User Story 2 - Progress Through Learning Sections (Priority: P1)

As a learner, I can see which sections are complete or available and make progress according to the course's navigation mode.

**Why this priority**: Learners need a clear and enforceable path through text, quiz, and lab activities.

**Independent Test**: In a course with ordered text, quiz, and lab sections, exercise both modes and verify direct access, completion, and course-completion eligibility.

**Acceptance Scenarios**:

1. **Given** a `FREE` course, **When** a learner opens any published section, **Then** access is allowed regardless of earlier section completion.
2. **Given** a `SEQUENTIAL` course, **When** a learner opens a later section before completing the current required section, **Then** access is denied and the response identifies the blocking section.
3. **Given** a learner opens an earlier unlocked section again, **When** they request it, **Then** access remains allowed.
4. **Given** a text section, **When** the learner marks it complete, **Then** completion is persisted for that learner and section.
5. **Given** an ordinary quiz with `requires_pass=false`, **When** the learner submits it, **Then** the quiz section is complete for sequential progression.
6. **Given** an ordinary quiz with `requires_pass=true`, **When** the learner has not passed, **Then** a sequential course keeps later sections locked; in a free course later sections remain accessible, while the required pass remains necessary for course completion.
7. **Given** a Lab Task in a sequential course, **When** the learner has not submitted a task, **Then** later sections stay locked; after the learner submits, later sections unlock without waiting for review. The lab satisfies course completion after admin review without a revision request when requires_pass=false, and must reach PASSED when requires_pass=true.
8. **Given** an exam section, **When** the learner has not attempted or passed it, **Then** it does not block later sections or course completion.
9. **Given** all applicable completion requirements are met, **When** course completion is requested, **Then** the enrollment may be marked `COMPLETED` through the established completion workflow.

### User Story 3 - Submit and Review Lab Tasks (Priority: P1)

As a learner, I can submit a lab task with written work, evidence links, and uploaded files, receive review feedback, and revise it when requested. As an administrator or instructor, I can review submissions, assign a score, and pass the task.

**Why this priority**: Lab activities require a learner deliverable and a review outcome that contributes to course completion.

**Independent Test**: Submit a lab task, review it as an administrator, request a revision, submit a revision, and pass it with a score.

**Acceptance Scenarios**:

1. **Given** a learner enrolled in a course with a lab section, **When** they submit a task, **Then** the submission must contain text and at least one HTTP(S) link or uploaded file.
2. **Given** a learner's first submission, **When** it is saved, **Then** a per-learner, per-section `CollectTask` is created with status `SUBMITTED`.
3. **Given** a submitted task, **When** an administrator begins review, **Then** its status becomes `IN_REVIEW`.
4. **Given** a task under review, **When** an administrator requests changes, **Then** status becomes `REVISION_REQUIRED`, a review note is required, and the review is recorded in history.
5. **Given** a learner revises a task, **When** they resubmit, **Then** the latest status returns to `SUBMITTED` and the earlier submission and review remain available.
6. **Given** a task under review, **When** an administrator completes the review without requesting revision, **Then** status becomes `REVIEWED` or `PASSED`, the score is within 0–100, and reviewer identity and review time are recorded.
7. **Given** a learner requests another learner's task or a non-administrator attempts review, **When** the request is handled, **Then** access is denied without exposing submission content.
8. **Given** a learner submits task files, **When** upload validation runs, **Then** no more than 10 files, 25 MB per file, and 100 MB total are accepted, and only PDF, DOCX, XLSX, PPTX, TXT, CSV, ZIP, PNG, JPG, or JPEG are allowed.
9. **Given** a file is attached to a submission, **When** a learner requests a revision, **Then** the earlier file remains associated with its original immutable submission history item.
10. **Given** a file is requested for download, **When** the caller is not its task owner, an administrator, or an instructor, **Then** access is denied and file bytes remain private.
11. **Given** a learner chooses a file, **When** the upload succeeds, **Then** its bytes and metadata are committed before task submission and the response returns a file ID that can be submitted within 24 hours for that learner and section.

## Edge Cases

- A learner cannot mark a quiz, exam, or lab section complete through the text-material completion action.
- A failed required quiz can be retried until passed; quiz `max_attempts` remains scoped to exams.
- An invalid, empty, or non-HTTP(S) evidence link is rejected before persistence.
- A learner cannot create duplicate current `CollectTask` records for one section; later submissions append history to the same task.
- Course/module/section ordering uses deterministic positions; archived or unpublished sections do not create learner-visible progression gates.
- A section's `requires_pass` setting is ignored for exams.
- Admin review records retain the reviewer, status decision, optional score, note, and timestamp; a note is mandatory for `REVISION_REQUIRED`.
- File metadata is stored in the database while private bytes are stored by a configurable local or S3-compatible adapter; development defaults to local storage.
- Uploaded file type is determined from an allowlisted extension and verified against basic file signatures where applicable; download responses force attachment and disable MIME sniffing.

## Requirements

### Functional Requirements

- **FR-001**: A Course MUST persist `progression_mode` with values `FREE` and `SEQUENTIAL`; the default MUST be `FREE` for existing and new courses.
- **FR-002**: A Course MUST persist `completion_mode` with values `SELF_LEARNING` and `ADMIN_REVIEW`; self-learning courses complete enrollments automatically after requirements are met, while admin-review courses require an administrator to review and mark completion.
- **FR-003**: A Section MUST persist `requires_pass`, defaulting to `false` for existing and new sections.
- **FR-004**: Course and section authoring operations MUST expose these settings only to authorized content editors.
- **FR-005**: Learner section access MUST be checked in application use cases for both section reads and quiz sitting starts.
- **FR-006**: A FREE course MUST allow direct access to any published section.
- **FR-007**: A SEQUENTIAL course MUST unlock sections in module/section position order after the preceding required activity is complete, including a Lab Task submission; unlocked earlier sections remain accessible.
- **FR-008**: Learners MUST be able to persist completion of text sections using an explicit completion action.
- **FR-009**: Ordinary quiz submission MUST complete a section when pass is not required. When pass is required, the quiz MUST use a configurable 0–100 passing score, defaulting to 70, and allow retries until passed.
- **FR-010**: Exam attempt limits MUST retain their existing behavior and exams MUST not gate section progression or course completion under this feature.
- **FR-011**: A Lab Task MUST unlock subsequent sections after learner submission without waiting for task review. A lab submission MUST be reviewed before satisfying course completion; when requires_pass=false, a review without a revision request is sufficient, and when requires_pass=true, status PASSED is required.
- **FR-012**: Course completion eligibility MUST require all text sections marked complete, all ordinary quizzes submitted, all required ordinary quizzes passed, all lab tasks reviewed without a revision request, and all required lab tasks passed; exams are excluded.
- **FR-013**: A `CollectTask` MUST represent the current learner workflow for one section, with at most one task per learner/section.
- **FR-014**: Every CollectTask submission MUST contain non-empty text and at least one valid HTTP(S) evidence link or uploaded file.
- **FR-015**: CollectTask status MUST support `SUBMITTED`, `IN_REVIEW`, `REVISION_REQUIRED`, `REVIEWED`, and `PASSED`, with transitions enforced by application use cases. `REVIEWED` records a completed review without asserting a pass.
- **FR-016**: Each submission and review MUST be retained as history, including text, evidence links, attached Files, status, score where assigned, review note, reviewer identity, and timestamps.
- **FR-017**: Administrators and instructors MUST be able to list tasks awaiting review, begin review, complete review with a 0–100 score as `REVIEWED` or `PASSED`, or request revision with a required note.
- **FR-018**: Learners MUST only read and modify their own CollectTask submissions; answer keys, other learner submissions, and credential data MUST not be exposed.
- **FR-019**: An admin-reviewed course MUST only become complete after an administrator reviews its required work and explicitly marks the learner's enrollment complete.
- **FR-020**: A self-learning course MUST automatically complete the learner's enrollment once all applicable course-completion requirements are met.
- **FR-021**: Learners MUST be able to upload up to 10 task files per submission, at 25 MB per file and 100 MB total; the allowed types are PDF, DOCX, XLSX, PPTX, TXT, CSV, ZIP, PNG, JPG, and JPEG. Each selected file is uploaded and committed separately before the task submission.
- **FR-022**: File bytes MUST be stored through a private local or S3-compatible adapter while the `files` table stores metadata; staged file metadata MUST be scoped to its uploader and section, expire after 24 hours, and be cleaned up when unattached. `collect_task_files` MUST associate each file with its CollectTask and immutable submission history item.
- **FR-023**: File downloads MUST be authorized for the task owner, `admin`, or `instructor`; object storage keys MUST remain private and absent from API responses.

### Key Entities

- **Course**: Owns progression mode, completion mode, Modules, and course-level completion policy.
- **Section**: Ordered learning activity with content type and optional pass requirement.
- **SectionCompletion**: Learner-specific completion record for text material.
- **CollectTask**: Current task workflow for one learner and one lab section.
- **CollectTaskSubmission**: Immutable submission/review history, with written response, evidence links, score, decision, feedback, reviewer, and timestamps.
- **Files**: Private file metadata; the M2M association identifies the exact CollectTask submission history version.
- **QuizSittingResult**: Existing assessment result used to determine ordinary quiz completion and passing.
- **Enrollment**: Existing learner/course participation whose completion eligibility is derived from required learning activities.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Editors can persist and read course progression mode and section pass settings, with defaults matching existing free-access behavior.
- **SC-002**: Learners cannot access a locked sequential section through either direct section reads or quiz-start operations.
- **SC-003**: Every accepted learner completion or lab submission is associated with the authenticated learner and exact course section.
- **SC-004**: Administrators can inspect the full task revision/review history and see the current status and score without changing prior submissions.
- **SC-005**: A course cannot be marked complete while any applicable requirement remains incomplete.
- **SC-006**: Existing exam attempt limits and learner result confidentiality remain intact.
- **SC-007**: File revisions remain attached to their original task history entries, and unauthorized learner downloads are denied.

## Assumptions

- Existing `Section` HTTP routes remain compatibility routes; canonical domain naming remains `Chapter` and `KnowledgeQuiz` where applicable.
- Passing score for an ordinary required quiz is an editor-configurable percentage from 0 to 100, defaulting to 70.
- Course content ordering follows Module position, then Section position, with stable identity as a tie-breaker.
- Lab submission fields use text plus one or more HTTP(S) links or private file attachments.
- Existing Courses migrate to `ADMIN_REVIEW`; new Courses default to `SELF_LEARNING`.
- In `ADMIN_REVIEW` mode, the existing authorized administrator completion action remains the final step after eligibility checks. In `SELF_LEARNING` mode, eligibility automatically completes the enrollment.
