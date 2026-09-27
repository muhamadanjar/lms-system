# Research: Enhanced Quiz Sitting Results

**Feature**: Enhanced Quiz Sitting Results  
**Date**: 2026-09-28

## Decision 1: Extend the current quiz seam instead of creating a parallel assessment module

**Decision**: Extend the existing `Quiz`, `Question`, `Answer`, `QuizSitting`, SQLModel
repositories, and unit of work. Add focused behavior and ports only where the new workflow
needs them.

**Rationale**: The project already has persisted quiz and sitting entities, including a
single-active-draft check and an attempt-state value object. A second hierarchy would duplicate
identity, state, and cascade behavior without a consumer.

**Alternatives considered**:

- A separate assessment package: rejected because it duplicates existing active persistence
  seams and violates the no-unused-abstraction rule.
- Store result JSON directly on `quiz_sittings`: rejected because code partition, immutable
  snapshots, answer selection validation, and audit queries would be opaque.

## Decision 2: Question codes are canonical normalized values backed by a durable allocator

**Decision**: Store the trimmed-uppercase `question_code` on `questions` as a non-null,
globally unique value. A `question_code_sequences` persistence record allocates generated
`Q-000001` values in the same transaction; manual codes are validated through the same global
namespace.

**Rationale**: Global uniqueness cannot be protected by the existing `(quiz_id, position)`
constraint or a `MAX(question_code)` query under concurrent requests. Persisting the normalized
value makes uniqueness portable across supported database collations.

**Alternatives considered**:

- Reuse Question slug: rejected because slug is a separate global content identity and does
  not have the user-required `Q-000001` behavior.
- Generate from row IDs or timestamps: rejected because generated values are not predictable
  and concurrent ordering is difficult to audit.
- Use a PostgreSQL-only sequence: rejected because project test/development storage is not
  PostgreSQL-only.

## Decision 3: Freeze complete evaluation material when a sitting starts

**Decision**: At start/resume, create a Question Snapshot and Option Snapshot for every
available multiple-choice question, including code, order, answer policy, option identity,
display value, and protected correctness marker. Draft selections reference snapshot options.

**Rationale**: The agreed sitting snapshot applies while the sitting is in progress as well as
after it is final. Retaining only question codes would let later option or correct-answer edits
change a learner's score. Snapshot option correctness is persistence-only evaluation material
and never appears in learner result DTOs or logs.

**Alternatives considered**:

- Read current question/answers during finalization: rejected because it makes historical
  grading mutable.
- Snapshot question codes only: rejected because it cannot reproduce the learner-visible
  options or evaluate after author edits.
- Snapshot answer keys in a learner response: rejected because it leaks protected data.

## Decision 4: Finalization is one domain operation and one unit-of-work transaction

**Decision**: Add a domain `finalize` behavior. It validates draft selections against snapshot
options, evaluates exact answer sets, produces exactly one result for every snapshot question,
sets the total, and advances the existing internal state path to `GRADED` within one transaction.
When an already graded sitting is finalized again, the use case returns the persisted result.

**Rationale**: The current generic `transition_sitting` only changes state and cannot preserve
result atomicity. Treating the graded sitting as the idempotency resource handles a lost HTTP
response without needing a separate idempotency-key feature.

**Alternatives considered**:

- Evaluate in the router: rejected because scoring and state invariants are domain rules.
- Persist a partial result per submitted answer: rejected because scores are only final after
  the learner finalizes.
- Add an HTTP idempotency key: rejected because retrying a specific finalized sitting is
  sufficient for this feature.

## Decision 5: Multiple-choice scoring is fixed and exact; legacy direct questions are blocked

**Decision**: A `MULTICHOICE` Question scores 1 only when its selected snapshot-option set
exactly equals the correct set under the quiz answer policy; otherwise it scores 0. Existing
`DIRECT` questions are preserved but a sitting that contains one is rejected before start with a
deterministic validation error until a direct-answer scoring specification is approved.

**Rationale**: The feature specification fixes multiple-choice scoring at 1/0 and says
non-multiple-choice weighting is out of scope. Silently applying the legacy `weight` field or
treating direct answers as multiple-choice would change quiz semantics without a specification.

**Alternatives considered**:

- Apply the existing `weight` to multiple-choice scores: rejected by FR-009.
- Automatically score direct answers with string equality: rejected because normalization,
  feedback, and accepted-answer semantics are unspecified.

## Decision 6: Exam limits are serialized at finalization; practice uses best-score projection

**Decision**: `Quiz.is_exam` defaults to false and `max_attempts` defaults to 1 when exam is
enabled. A per-quiz/per-learner exam counter is locked and incremented in the same finalization
transaction as result creation. Non-exams never use that counter and summarize `MAX(total_score)`
across graded sittings.

**Rationale**: The current repository only checks for an active draft, which is race-prone and
does not count finalized attempts. Enforcing only at start can be bypassed by simultaneous
drafts; enforcing within finalization provides a durable boundary.

**Alternatives considered**:

- Count graded rows without locking: rejected because simultaneous finalization can pass the
  same count.
- Limit non-exams too: rejected by the agreed product policy.

## Decision 7: Use database constraints plus transaction locking for concurrency-sensitive rules

**Decision**: Add a nullable unique active-sitting key to `quiz_sittings`, set only for an
in-progress sitting, so one learner/quiz has at most one active draft on all supported databases.
Use the exam counter's unique key and row locking/retry policy to serialize exam finalization.

**Rationale**: The current active-sitting lookup is an application-level check only. A database
constraint remains correct across simultaneous application workers; transaction locking protects
the dynamic exam ceiling.

**Alternatives considered**:

- Keep lookup-only validation: rejected because concurrent requests can create duplicate
  drafts.
- Use a PostgreSQL partial index as the only guard: rejected because it is less portable than a
  nullable unique key.

## Decision 8: Keep the current API conventions and put authorization in the application layer

**Decision**: Add a quiz/sitting router under `/api`, use existing Bearer identity extraction,
existing success/error envelopes, and nested course/module/section ownership routes. The
application use case checks sitting ownership; existing `admin`/`instructor` management policy
is the initial staff-result access policy because no enrollment policy exists yet.

**Rationale**: The existing HTTP contract and auth adapter already define error mappings and
delivery conventions. Keeping authorization out of the router meets the architecture rule and
avoids inventing a learner-enrollment model.

**Alternatives considered**:

- Add a new API version or top-level authorization service: rejected because neither is needed
  to make this feature safe.
- Return another learner's sitting as forbidden: rejected because a 404 avoids unnecessary
  existence disclosure to a learner.

## Decision 9: Backfill before constraining and retain a reversible recovery path

**Decision**: The Alembic revision adds nullable code/configuration/snapshot storage, backfills
legacy Questions in deterministic `created_at, id` order, seeds the allocator to the next value,
then applies non-null and uniqueness constraints. Downgrade removes dependent snapshot rows and
new fields in reverse dependency order; production rollout requires a database backup before
downgrade.

**Rationale**: Existing Questions have no codes and existing Sittings have no results. A
deterministic backfill preserves content and answer policies while making the new constraint
safe to apply.

**Alternatives considered**:

- Make the code non-null immediately: rejected because legacy rows would fail migration.
- Leave codes nullable forever: rejected because every question needs a code.
