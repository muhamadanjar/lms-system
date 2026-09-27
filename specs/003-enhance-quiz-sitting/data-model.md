# Data Model: Enhanced Quiz Sitting Results

## Existing Models Extended

### `quizzes`

| Field | Rule | Notes |
|---|---|---|
| `is_exam` | Boolean, required, default false | Enables configured finalized-attempt limit. |
| `max_attempts` | Positive integer, required, default 1 | Enforced only when `is_exam` is true. |
| `answer_policy` | `SINGLE` or `MULTIPLE`, required | Governs selected-option cardinality and exact-set evaluation. Existing data defaults to `MULTIPLE`. |

Configuration is immutable after the first sitting starts for that quiz. This avoids changing
the rules of an active or historical attempt.

### `questions`

| Field | Rule | Notes |
|---|---|---|
| `question_code` | String, required, globally unique | Stored normalized: trimmed and uppercase. Generated as `Q-000001` when missing after trim. |

`question_code` is mutable only while the Question remains draft. A published Question retains
its code forever. The existing `weight` remains stored for compatibility but does not affect
the fixed 1/0 score of `MULTICHOICE` Questions in this feature.

### `quiz_sittings`

| Field | Rule | Notes |
|---|---|---|
| `active_sitting_key` | Nullable, unique | `quiz_id:learner_id` while `IN_PROGRESS`; cleared on finalization/cancellation. |
| `total_score` | Nullable numeric/integer | Set only when state is `GRADED`; equals the sum of result scores. |

The existing `attempt_state` lifecycle remains `IN_PROGRESS → SUBMITTED → GRADED` internally.
The new finalization behavior performs the two transitions within its transaction; `GRADED`
means final and immutable.

## New Persistence Records

### `question_code_sequences`

| Field | Rule | Notes |
|---|---|---|
| `name` | Primary key | Singleton `question_code`. |
| `next_value` | Positive integer | Next generated numeric suffix. |
| `updated_at` | UTC datetime | Audit and lock/update timestamp. |

The allocator locks this record while issuing generated codes. Manual codes share the Question
unique constraint; a manually inserted `Q-` code cannot produce a duplicate generated code.

### `quiz_sitting_questions`

| Field | Rule | Notes |
|---|---|---|
| `id` | UUID, primary key | Snapshot identity. |
| `sitting_id` | Required FK | References `quiz_sittings.id`, cascade delete. |
| `source_question_id` | Required FK/reference | Source Question at sitting start; retained for audit. |
| `question_code` | Required string | Frozen normalized code. |
| `prompt` | Required text | Learner-visible snapshot. |
| `question_type` | Required enum | Only `MULTICHOICE` is eligible in this feature. |
| `answer_policy` | Required enum | Frozen quiz policy. |
| `position` | Required positive integer | Stable presentation/evaluation order. |

Constraints: `UNIQUE(sitting_id, question_code)`, `UNIQUE(sitting_id, position)`, and an index
on `(sitting_id, position, id)`.

### `quiz_sitting_options`

| Field | Rule | Notes |
|---|---|---|
| `id` | UUID, primary key | Snapshot option identity used by learner selections. |
| `sitting_question_id` | Required FK | References `quiz_sitting_questions.id`, cascade delete. |
| `source_answer_id` | Required FK/reference | Source option at start. |
| `value` | Required text | Frozen learner-visible option text. |
| `position` | Required positive integer | Stable option order. |
| `is_correct` | Required boolean | Protected evaluator-only material; never projected to learner DTOs/logs. |

Constraints: `UNIQUE(sitting_question_id, position)` and an index on the parent snapshot.

### `quiz_sitting_answer_selections`

| Field | Rule | Notes |
|---|---|---|
| `sitting_question_id` | Required FK | References `quiz_sitting_questions.id`, cascade delete. |
| `sitting_option_id` | Required FK | References `quiz_sitting_options.id`, cascade delete. |

The composite primary key is `(sitting_question_id, sitting_option_id)`. Selections are mutable
only while the parent Sitting is in progress. The application validates that option and question
belong to the same Sitting and that the cardinality respects `answer_policy`.

### `quiz_sitting_question_results`

| Field | Rule | Notes |
|---|---|---|
| `sitting_question_id` | Primary/unique FK | One result for every snapshot question. |
| `question_code` | Required string | Denormalized immutable projection key. |
| `outcome` | `ANSWERED`, `WRONG`, or `UNANSWERED` | Used to produce required code lists. |
| `score` | Integer, required | `1` for correct multichoice; `0` otherwise. |
| `finalized_at` | UTC datetime, required | Finalization audit time. |

The result table is written only during finalization. Result rows and `quiz_sittings.total_score`
are immutable after state becomes `GRADED`.

### `quiz_exam_attempt_counters`

| Field | Rule | Notes |
|---|---|---|
| `quiz_id` | Required FK | Part of composite primary key. |
| `learner_id` | Required string | Part of composite primary key. |
| `finalized_attempts` | Non-negative integer | Incremented only while finalizing an exam sitting. |
| `updated_at` | UTC datetime | Lock/audit timestamp. |

The application locks this record in the same transaction as finalization, rejects a count at
the configured maximum, and increments only after the result can be committed. Non-exam
sittings neither read nor write it.

## Aggregate and State Rules

```text
Quiz
 ├── Questions (globally unique QuestionCode)
 └── QuizSittings (one active draft per learner)
      ├── Question Snapshots
      │    ├── Option Snapshots
      │    ├── Draft Selections
      │    └── Immutable Question Result after finalization
      └── total_score after finalization
```

1. `available_question_codes` is the ordered projection of Question Snapshots.
2. `question_answer`, `question_wrong`, and `question_unanswered` are disjoint projections of
   Question Results. Their union is exactly `available_question_codes`.
3. `question_scores` has exactly one entry per available code. `total_score` is their sum.
4. Finalization validates the complete selected-option set: a multiple-answer Question is
   correct only when its selection equals its correct snapshot-option set.
5. A final retry reads the existing `GRADED` results rather than changing state or writing new
   rows.
6. Non-exam canonical score is `MAX(total_score)` among graded sittings. All ties/history stay
   persisted.

## Migration and Recovery

1. Add quiz configuration fields and nullable `questions.question_code`.
2. Backfill every existing Question in `created_at, id` order with `Q-000001` onward.
3. Seed `question_code_sequences.next_value` after the final allocated suffix.
4. Apply the global non-null unique code constraint and add snapshot, selection, result,
   active-key, and exam-counter records with named indexes/foreign keys.
5. On downgrade, remove dependent sitting records before fields/tables in reverse dependency
   order. A production operator takes a database backup before a rollback because snapshot and
   result history introduced after upgrade is removed by downgrade.
