# Data Model: Course Module Section Persistence

## Conventions

- Table names use `snake_case` plural nouns.
- Primary keys use application-generated UUID values.
- Every persisted model has `id`, `slug`, `status`, `created_at`, and `updated_at` unless
  explicitly noted.
- `status` uses the portable values `DRAFT`, `PUBLISHED`, and `ARCHIVED`.
- Timestamps are UTC-aware and `created_at` is immutable.
- Slug values are immutable and globally unique through `content_slug_registry`.
- Foreign keys are named and use `ON DELETE CASCADE` where specified.
- Child collections are read using `position ASC, id ASC`.

## Tables

### `courses`

| Field | Type/Rule | Notes |
|---|---|---|
| `id` | UUID, primary key | Application-generated. |
| `slug` | string, required | User-readable, immutable; mirrored in registry. |
| `status` | ContentStatus, required | Defaults to `DRAFT`. |
| `title` | string, required | Trimmed and length-validated. |
| `description` | text, nullable | Optional authoring metadata. |
| `created_at` | UTC datetime, required | Immutable. |
| `updated_at` | UTC datetime, required | Updated on mutation. |

Relationships: one Course has many Modules. Deleting a Course cascades to Modules, Sections,
detail models, quiz content, sittings, and the Course slug registry entry in one unit of work.

### `modules`

| Field | Type/Rule | Notes |
|---|---|---|
| `id` | UUID, primary key | Application-generated. |
| `course_id` | UUID, required FK | References `courses.id`, `ON DELETE CASCADE`. |
| `slug` | string, required | Immutable and globally registered. |
| `status` | ContentStatus, required | Defaults to `DRAFT`. |
| `title` | string, required | Trimmed and length-validated. |
| `description` | text, nullable | Optional. |
| `position` | positive integer, required | Unique within Course. |
| `created_at` | UTC datetime, required | Immutable. |
| `updated_at` | UTC datetime, required | Updated on mutation. |

Constraints: `UNIQUE(course_id, position)` and an index on `(course_id, position, id)`.

### `sections`

| Field | Type/Rule | Notes |
|---|---|---|
| `id` | UUID, primary key | Application-generated. |
| `module_id` | UUID, required FK | References `modules.id`, `ON DELETE CASCADE`. |
| `slug` | string, required | Immutable and globally registered. |
| `status` | ContentStatus, required | Defaults to `DRAFT`. |
| `title` | string, required | Trimmed and length-validated. |
| `description` | text, nullable | Optional. |
| `position` | positive integer, required | Unique within Module. |
| `content_type` | SectionContentType, required | `MATERIAL`, `LAB_TASK`, or `QUIZ`. |
| `created_at` | UTC datetime, required | Immutable. |
| `updated_at` | UTC datetime, required | Updated on mutation. |

Constraints: `UNIQUE(module_id, position)` and an index on `(module_id, position, id)`.
Exactly one matching detail relation is required for `LAB_TASK` and `QUIZ`; `MATERIAL` has no
additional detail table in this initial slice.

### `lab_environment_settings`

| Field | Type/Rule | Notes |
|---|---|---|
| `id` | UUID, primary key | Application-generated. |
| `section_id` | UUID, required unique FK | References a `LAB_TASK` Section, cascade delete. |
| `slug` | string, required | Immutable and globally registered. |
| `status` | ContentStatus, required | Defaults to `DRAFT`. |
| `provider` | string, required | Provider-neutral adapter key. |
| `region` | string, nullable | Provider region/zone. |
| `image` | string, required | Requested lab image identifier. |
| `cpu` | positive integer, required | Resource request. |
| `memory_mb` | positive integer, required | Resource request. |
| `storage_gb` | positive integer, nullable | Resource request. |
| `access_method` | enum, required | `PASSWORD` or `PUBLIC_KEY`. |
| `username` | string, required | Non-secret login metadata. |
| `password_secret_ref` | string, nullable | Required for `PASSWORD`; opaque reference only. |
| `public_key` | text, nullable | Public key material; never private key. |
| `private_key_secret_ref` | string, nullable | Required for `PUBLIC_KEY`; opaque reference only. |
| `network_policy` | JSON/text, nullable | Validated provider-neutral constraints. |
| `timeout_seconds` | positive integer, required | Maximum lab lifetime/request timeout. |
| `cleanup_policy` | enum/string, required | Describes automatic cleanup behavior. |
| `created_at` | UTC datetime, required | Immutable. |
| `updated_at` | UTC datetime, required | Updated on mutation. |

Constraints: `UNIQUE(section_id)`; application validation enforces access-method-specific
credential references and rejects raw password/private-key values.

### `quizzes`

| Field | Type/Rule | Notes |
|---|---|---|
| `id` | UUID, primary key | Application-generated. |
| `section_id` | UUID, required unique FK | References a `QUIZ` Section, cascade delete. |
| `slug` | string, required | Immutable and globally registered. |
| `status` | ContentStatus, required | Defaults to `DRAFT`. |
| `created_at` | UTC datetime, required | Immutable. |
| `updated_at` | UTC datetime, required | Updated on mutation. |

Constraints: `UNIQUE(section_id)`. Quiz-specific configuration not required by the initial
feature remains extensible for later migrations.

### `questions`

| Field | Type/Rule | Notes |
|---|---|---|
| `id` | UUID, primary key | Application-generated. |
| `quiz_id` | UUID, required FK | References `quizzes.id`, cascade delete. |
| `slug` | string, required | Immutable and globally registered. |
| `status` | ContentStatus, required | Defaults to `DRAFT`. |
| `prompt` | text, required | Question text. |
| `question_type` | enum, required | `MULTICHOICE` or `DIRECT`. |
| `weight` | positive decimal, required | Instructor-defined scoring weight. |
| `position` | positive integer, required | Unique within Quiz. |
| `created_at` | UTC datetime, required | Immutable. |
| `updated_at` | UTC datetime, required | Updated on mutation. |

Constraints: `UNIQUE(quiz_id, position)` and index `(quiz_id, position, id)`.

### `answers`

| Field | Type/Rule | Notes |
|---|---|---|
| `id` | UUID, primary key | Application-generated. |
| `question_id` | UUID, required FK | References `questions.id`, cascade delete. |
| `slug` | string, required | Immutable and globally registered. |
| `status` | ContentStatus, required | Defaults to `DRAFT`. |
| `value` | text, required | Option text or accepted direct-answer value. |
| `is_correct` | boolean, nullable | Required for `MULTICHOICE`; ignored/rejected for `DIRECT` as configured. |
| `position` | positive integer, required | Stable option ordering. |
| `created_at` | UTC datetime, required | Immutable. |
| `updated_at` | UTC datetime, required | Updated on mutation. |

Constraints: `UNIQUE(question_id, position)` and no duplicate normalized option values within
one question. At least one correct answer is required for a published `MULTICHOICE` question.

### `quiz_sittings`

| Field | Type/Rule | Notes |
|---|---|---|
| `id` | UUID, primary key | Application-generated. |
| `quiz_id` | UUID, required FK | References `quizzes.id`, cascade delete. |
| `learner_id` | UUID/string, required | External identity reference; no user FK in this feature. |
| `slug` | string, required | Immutable and globally registered. |
| `status` | ContentStatus, required | Shared model status, defaults to `DRAFT`. |
| `attempt_state` | enum, required | `IN_PROGRESS`, `SUBMITTED`, `GRADED`, or `CANCELLED`. |
| `started_at` | UTC datetime, required | Attempt start. |
| `submitted_at` | UTC datetime, nullable | Required after submission. |
| `created_at` | UTC datetime, required | Immutable. |
| `updated_at` | UTC datetime, required | Updated on mutation. |

Constraints: at most one active `IN_PROGRESS` sitting per learner and Quiz; exact historical
attempt policy remains an application rule for the next feature slice.

### `content_slug_registry`

| Field | Type/Rule | Notes |
|---|---|---|
| `slug` | string, primary key | Global unique namespace. |
| `content_id` | UUID, required | Polymorphic content identifier. |
| `content_kind` | string, required | Model discriminator. |
| `created_at` | UTC datetime, required | Registry creation time. |

The registry has no polymorphic database foreign key. Repository/unit-of-work code MUST create,
update, and delete registry entries atomically with their owning content rows.

## State Rules

### Shared Content Status

All persisted models default to `DRAFT`. `PUBLISHED` makes content eligible for user-facing
reads. `ARCHIVED` removes it from active reads while retaining the row until an explicit hard
delete operation. Invalid transitions are rejected by the domain/application policy.

### Quiz Sitting Attempt State

`IN_PROGRESS → SUBMITTED → GRADED` is the normal path. `IN_PROGRESS → CANCELLED` and
`SUBMITTED → CANCELLED` are failure/administrative paths. A graded sitting cannot return to
`IN_PROGRESS`.

## Cross-Table Invariants

1. A Section with `content_type=LAB_TASK` has exactly one LabEnvironmentSettings row.
2. A Section with `content_type=QUIZ` has exactly one Quiz row.
3. A Section with `content_type=MATERIAL` has neither detail row in this feature.
4. A Quiz Question belongs to exactly one Quiz; an Answer belongs to exactly one Question.
5. `MULTICHOICE` questions require at least one correct Answer before publication.
6. `DIRECT` questions use accepted Answer values and do not expose answer keys to learners.
7. Secret references are opaque and raw credentials are never persisted.
