# Data Model: Course Enrollment

**Feature**: specs/005-course-enrollment/spec.md | **Plan**: specs/005-course-enrollment/plan.md

## Entities

### Enrollment (NEW)

- Identity: `id: UUID`
- Owner: `user_id: str` (opaque, stripped non-empty)
- Scope: `course_id: UUID` (FK `courses.id`, immutable)
- Lifecycle: `status: ENROLLED | COMPLETED | WITHDRAWN` (default ENROLLED)
- Dates: `enrolled_at: datetime tz-aware` (default now, backdatable on create only), `completed_at: datetime tz-aware | None`
- Audit: `created_at, updated_at: datetime tz-aware UTC`

**Invariants**:

- `user_id`, `course_id` required; pair immutable after creation.
- Exactly one live (`ENROLLED`) row per `(user_id, course_id)` — partial unique index `uq_enrollments_user_course_live WHERE status = 'ENROLLED'`.
- `COMPLETED` requires non-null `completed_at`; `ENROLLED`/`WITHDRAWN` require null `completed_at`.
- `enrolled_at`, `created_at`, `updated_at` must be timezone-aware.
- Transitions: `ENROLLED --complete()--> COMPLETED`, `ENROLLED --withdraw()--> WITHDRAWN`; terminal states have no outgoing transitions. Re-enrollment = new row.

## Tables

### `enrollments` (NEW)

```text
id UUID PK
user_id VARCHAR(255) NOT NULL INDEX
course_id UUID NOT NULL FK courses.id ON DELETE CASCADE INDEX
status VARCHAR(10) NOT NULL DEFAULT 'ENROLLED' INDEX  -- ENROLLED | COMPLETED | WITHDRAWN
enrolled_at TIMESTAMPTZ NOT NULL
completed_at TIMESTAMPTZ NULL
created_at TIMESTAMPTZ NOT NULL
updated_at TIMESTAMPTZ NOT NULL
UNIQUE (user_id, course_id) WHERE status = 'ENROLLED'
```

### Migration `0009_course_enrollment` (additive, reversible)

Create table + indexes; downgrade drops them. No data backfill (no legacy participant data exists).

## Repository port (`EnrollmentRepository`)

```text
create(enrollment) -> enrollment      # Conflict on duplicate live (user, course)
update(enrollment) -> enrollment      # complete/withdraw transitions; owner+course immutable
get_live(user_id, course_id) -> enrollment | None
list_live_by_course(course_id) -> list[enrollment]
list_history(user_id, course_id) -> list[enrollment]  # all episodes, newest first
```

## API DTO (`EnrollmentRead`)

`{ id, user_id, course_id, status, enrolled_at, completed_at, created_at, updated_at }` — no secrets involved.
