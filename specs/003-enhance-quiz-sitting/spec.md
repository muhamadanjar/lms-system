# Feature Specification: Enhanced Quiz Sitting Results

**Feature Branch**: `main`

**Created**: 2026-09-28

**Status**: Draft

**Input**: User description: "Enhance quiz sitting so users can see which questions they answered and the score for each question. Use globally unique question codes, allow manual codes, and provide answer/wrong lists."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Finalize a quiz with auditable results (Priority: P1)

As a learner, I can finalize a quiz sitting and see every question that was available to
me, which questions I answered correctly or incorrectly, which I left unanswered, and my
score for each question plus the total score.

**Why this priority**: Learners and learning administrators need a complete, stable result
for every finalized attempt; without it, they cannot tell what the score represents.

**Independent Test**: Finalize a quiz containing answered-correctly, answered-incorrectly,
and unanswered questions, then retrieve the result and verify the complete classification
and scores.

**Acceptance Scenarios**:

1. **Given** a learner has an active sitting with a snapshot of three available questions,
   **When** the learner finalizes it with one correct answer, one incorrect answer, and one
   unanswered question, **Then** the result lists all three question codes, separates them
   into `question_answer`, `question_wrong`, and `question_unanswered`, assigns scores of
   1, 0, and 0 respectively, and reports a total score of 1.
2. **Given** a sitting is finalized, **When** the learner retrieves it later after the quiz
   has been edited, **Then** its available-question list, classifications, and scores remain
   unchanged.
3. **Given** a learner finalizes a sitting successfully but does not receive the response,
   **When** the learner retries the same finalization, **Then** the same finalized result is
   returned without another result or attempt being created.

---

### User Story 2 - Manage unique question codes (Priority: P1)

As a content author, I can rely on each question having a stable code that distinguishes it
from every other question in the learning system, whether the system generated it or I
entered it manually.

**Why this priority**: Stable codes make results readable, support auditability across
quiz revisions, and prevent ambiguous result lists.

**Independent Test**: Create questions with generated and manual codes, then attempt to
create or update another question with an equivalent manual code.

**Acceptance Scenarios**:

1. **Given** a new question is created without a code, **When** it is saved, **Then** it
   receives a system-generated code in the `Q-000001` pattern or its next unique sequence.
2. **Given** a content author enters a manual code, **When** it differs only by surrounding
   whitespace or letter case from an existing code, **Then** the system rejects it as a
   duplicate.
3. **Given** a question has been published, **When** an author attempts to change its code,
   **Then** the system rejects the change and preserves the original code.
4. **Given** questions existed before this feature, **When** the feature is adopted,
   **Then** each existing question receives a unique generated code without changing its
   learning content or correct-answer policy.

---

### User Story 3 - Enforce quiz attempt policy (Priority: P2)

As a learner, I can take practice quizzes repeatedly, while exam quizzes apply the
attempt limit set by their author, defaulting to one finalized attempt.

**Why this priority**: Practice and examination workflows have different assessment
expectations, and the result history must respect both.

**Independent Test**: Finalize multiple sittings for a practice quiz and an exam quiz with
a finite attempt limit, then verify the permitted and rejected starts.

**Acceptance Scenarios**:

1. **Given** a non-exam quiz, **When** a learner finalizes a sitting, **Then** the learner
   may start and finalize another sitting for the same quiz.
2. **Given** an exam quiz with no explicit attempt limit, **When** a learner has finalized
   one sitting, **Then** the learner cannot start another sitting.
3. **Given** an exam quiz with `max_attempts` set to 3, **When** a learner has finalized
   three sittings, **Then** the learner cannot start a fourth sitting.
4. **Given** a non-exam quiz with multiple finalized sittings, **When** a learner's quiz
   result is summarized for progress or completion, **Then** the highest total score is the
   canonical result while every finalized sitting remains available as history.

### Edge Cases

- A code that becomes empty after trimming is treated as absent and receives a generated
  code; a manually supplied non-empty code must normalize successfully before uniqueness is
  checked.
- A question code may appear exactly once across the three outcome lists, and together the
  outcome lists must contain every available question code from that sitting.
- A finalized sitting never recalculates outcomes when an author changes options, answer
  policies, or correct answers in the current quiz.
- A finalization failure before the result is saved leaves the sitting unfinalized and
  retryable; no partial score is exposed as a final result.
- A learner cannot use concurrent drafts to bypass an exam's configured finalized-attempt
  limit.
- Correct-answer choices and other learners' answers are never exposed in a learner's
  sitting result.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST assign every question one globally unique `question_code`.
- **FR-002**: The system MUST generate a unique `Q-000001`-style code when an author does
  not provide a code, and MUST accept a manually provided code only when its normalized form
  is globally unique.
- **FR-003**: The system MUST normalize manual codes by trimming whitespace and converting
  letters to uppercase before storing and checking uniqueness.
- **FR-004**: The system MUST preserve a published question's code and reject attempts to
  change it.
- **FR-005**: The system MUST assign a unique generated code to every pre-existing question
  as part of feature adoption.
- **FR-006**: A sitting MUST retain a snapshot of its `available_question_codes` when it is
  created; later quiz changes MUST NOT alter that snapshot.
- **FR-007**: On successful finalization, the system MUST produce `question_answer`,
  `question_wrong`, and `question_unanswered` as mutually exclusive lists of question codes
  whose union equals `available_question_codes`.
- **FR-008**: On successful finalization, the system MUST provide a score for every available
  question code and a total score equal to the sum of those question scores.
- **FR-009**: For the currently supported multiple-choice questions, a correct answer MUST
  score 1 and an incorrect or unanswered question MUST score 0. Question weighting is out of
  scope until a non-multiple-choice question type is specified.
- **FR-010**: The system MUST evaluate a multiple-answer question against its complete
  correct-answer set according to the quiz's answer policy before classifying it as correct.
- **FR-011**: The system MUST calculate and persist result lists and scores only when a
  sitting is finalized; a draft sitting MUST not expose a final score or final outcome lists.
- **FR-012**: A finalized sitting MUST be immutable with respect to learner answers and
  evaluation outcomes.
- **FR-013**: Finalization retries after a successful save MUST return the original finalized
  result without creating another result or score; retries after a failure before save MUST
  remain possible.
- **FR-014**: A non-exam quiz MUST permit unlimited finalized sittings per learner and use
  the highest finalized total score as its canonical progress result.
- **FR-015**: An exam quiz MUST enforce its configured `max_attempts` against finalized
  sittings; the default must be one, and the limit does not apply to non-exam quizzes.
- **FR-016**: The system MUST retain every finalized sitting as learner history, including
  when a later non-exam sitting becomes the highest-scoring result.
- **FR-017**: The system MUST authorize learners to create, answer, finalize, and view only
  their own sittings, while authorized learning staff may view results according to the
  existing course-access policy.
- **FR-018**: Learner-facing results MUST NOT reveal correct-answer choices, answer keys, or
  another learner's submitted answers.

### Key Entities

- **Question**: A quiz prompt with a stable, globally unique question code and an answer
  policy.
- **Quiz Configuration**: The quiz's exam classification and, for exams, its allowed number
  of finalized attempts.
- **Quiz Sitting**: One learner's in-progress or finalized encounter with a snapshot of the
  quiz's available question codes.
- **Question Result**: The immutable finalized classification and score for one question
  code in a sitting.
- **Quiz Result Summary**: The canonical progress result for a learner and quiz; for
  non-exams it is the highest finalized total score.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For 100% of finalized sittings, every available question code appears exactly
  once across the correct, wrong, and unanswered outcome lists and has one score entry.
- **SC-002**: For 100% of valid finalization retries after a saved result, learners receive
  the original result without an extra sitting or changed score.
- **SC-003**: A duplicate code, including a case- or whitespace-only duplicate, is rejected
  before it can become available in a quiz.
- **SC-004**: 100% of attempts beyond an exam's configured finalized-attempt limit are
  refused, while a learner can finalize at least two sittings for a non-exam quiz.
- **SC-005**: Learners can identify the outcome and score of every question in a finalized
  sitting without seeing answer keys or other learners' answers.

## Assumptions

- An active draft sitting is resumed rather than replaced by a second active draft for the
  same learner and quiz; this prevents concurrent drafts from bypassing exam limits.
- Existing course-access authorization determines which learning staff may inspect learner
  results; this feature does not introduce a new role model.
- Code generation reserves the `Q-` prefix and advances to the next globally unused numeric
  sequence; manually entered codes are not required to use that prefix.
- Ties for a non-exam's highest total score are retained in history; the feature only defines
  the score value as canonical, not a preferred tied sitting.
- A sitting's historical evaluation is retained as finalized even if its source quiz is later
  edited or unpublished.
