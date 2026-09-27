# HTTP Contract: Quiz Sitting Results

All routes use the existing `/api` prefix, Bearer authentication, `{data, meta}` success
envelope, and `{error}` failure envelope. Routers extract identity and invoke an application use
case; quiz policy, ownership, scoring, and attempt limits do not live in HTTP handlers.

## Authorization

- An authenticated learner starts, saves, finalizes, and reads only their own sittings.
- `admin` and `instructor` use the existing management policy for question/quiz configuration
  and staff result reads until a course-enrollment access policy exists.
- A learner requesting another learner's sitting receives `404`.
- Missing/invalid credentials return `401`; unavailable User Management returns `503`.

## Routes

| Method | Route | Access | Behavior |
|---|---|---|---|
| PATCH | `/api/courses/{course_slug}/modules/{module_slug}/sections/{section_slug}/quiz` | admin/instructor | Set draft quiz `is_exam`, `max_attempts`, and answer policy. |
| POST | `/api/courses/{course_slug}/modules/{module_slug}/sections/{section_slug}/quiz/questions` | admin/instructor | Create Question; accepts optional manual `question_code`. |
| PATCH | `/api/courses/{course_slug}/modules/{module_slug}/sections/{section_slug}/quiz/questions/{question_slug}` | admin/instructor | Update a draft Question; published `question_code` cannot change. |
| POST | `/api/courses/{course_slug}/modules/{module_slug}/sections/{section_slug}/quiz/sittings` | learner | Start a sitting or resume the same active draft. Returns `201` when created and `200` when resumed. |
| PUT | `/api/quiz-sittings/{sitting_id}/answers` | owning learner | Replace/upsert draft selections by snapshot `question_code` and snapshot option IDs. |
| POST | `/api/quiz-sittings/{sitting_id}/finalize` | owning learner | Atomically evaluate and finalize; repeated call after a saved finalization returns the same result. |
| GET | `/api/quiz-sittings/{sitting_id}` | owner/authorized staff | Read draft metadata or immutable learner-safe final result. |
| GET | `/api/courses/{course_slug}/modules/{module_slug}/sections/{section_slug}/quiz/result` | learner | Read canonical summary: best score for non-exam, exam final result/attempt availability for exam. |

The normal nested route validates Course → Module → Section ownership and published learner
access before a sitting may start.

## Request Shapes

### Create or update Question

```json
{
  "prompt": "Which options are correct?",
  "question_code": " q-network-01 "
}
```

`question_code` is optional. A blank value becomes a generated code; a non-blank value is
stored as `Q-NETWORK-01`. Duplicate normalized codes return `409`; an attempted code change on
a published Question returns `422`.

### Configure an exam

```json
{
  "is_exam": true,
  "max_attempts": 3,
  "answer_policy": "MULTIPLE"
}
```

For `is_exam: true`, an omitted `max_attempts` becomes `1`. For non-exams, `max_attempts` is
stored for future configuration but is not enforced.

### Save draft answer selections

```json
{
  "answers": [
    {
      "question_code": "Q-000001",
      "option_ids": ["2a4c4f74-e6c8-4d5f-9baa-4f0d7d14e1f0"]
    }
  ]
}
```

Every code must be in the sitting snapshot. Option IDs must belong to that code's snapshot.
Duplicate codes, duplicate options, options from a different question, invalid single-answer
cardinality, and any mutation after finalization return `422`.

## Learner-safe Final Result

```json
{
  "data": {
    "id": "25fc6d86-9df0-4b9b-b4cc-31e0b0875ba5",
    "quiz_id": "4a7976ba-6db9-4e9e-9c06-2c00d6a2cb02",
    "attempt_state": "GRADED",
    "available_question_codes": ["Q-000001", "Q-000002", "Q-000003"],
    "question_answer": ["Q-000001"],
    "question_wrong": ["Q-000002"],
    "question_unanswered": ["Q-000003"],
    "question_scores": [
      {"question_code": "Q-000001", "score": 1},
      {"question_code": "Q-000002", "score": 0},
      {"question_code": "Q-000003", "score": 0}
    ],
    "total_score": 1,
    "finalized_at": "2026-09-28T10:00:00Z"
  },
  "meta": {}
}
```

This response never includes option correctness, correct option IDs, answer keys, raw draft
selections, or another learner's data.

## Error Contract

| Status | Code | Condition |
|---|---|---|
| 401 | `UNAUTHORIZED` | Missing or invalid bearer token. |
| 403 | `FORBIDDEN` | Authenticated caller lacks author/staff permission. |
| 404 | `RESOURCE_NOT_FOUND` | Unknown resource or another learner's sitting. |
| 409 | `QUESTION_CODE_CONFLICT` | Normalized global question-code collision. |
| 409 | `EXAM_ATTEMPT_LIMIT_REACHED` | Finalization would exceed the exam maximum. |
| 422 | `VALIDATION_ERROR` | Invalid question code, draft selection, unsupported direct question, or mutation of final content. |
| 503 | `AUTHENTICATION_SERVICE_UNAVAILABLE` | Delegated identity service unavailable. |
