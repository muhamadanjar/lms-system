# Research: Course Enrollment

**Feature**: specs/005-course-enrollment/spec.md | **Date**: 2026-09-28

All unknowns resolved in the grill; no NEEDS CLARIFICATION remains.

## Decision 1: Enrollment gates lab access

- **Decision**: `LabEnrollmentUseCases.enroll` checks live `ENROLLED` via the enrollment repo first; denial raises `AuthorizationError`-mapped `ENROLLMENT_REQUIRED` (403), distinct from capacity `CAPACITY_EXHAUSTED` (409).
- **Rationale**: Gives enrollment an active consumer from day one and protects the VPS pool.
- **Alternatives considered**: Independent roster — rejected, placeholder without consumer.

## Decision 2: Status model

- **Decision**: `ENROLLED` (live) / `COMPLETED` (terminal, keeps lab) / `WITHDRAWN` (terminal, releases lab). Live uniqueness enforced by partial unique index on `(user_id, course_id) WHERE status = 'ENROLLED'`.
- **Rationale**: Mirrors the proven `CourseLabAccess` ACTIVE/RELEASED pattern from 004.
- **Alternatives considered**: Boolean is_active — rejected, loses completion semantics needed for audit.

## Decision 3: Single date column

- **Decision**: `enrolled_at: datetime tz-aware`, defaults to now, admin-backdatable on create; `completed_at` nullable, required (non-null) exactly when status is COMPLETED. `created_at/updated_at` audit pair unchanged.
- **Rationale**: Avoids date_enrollment/created_at duplication while honoring the requested enrollment date + import backdate need.
- **Alternatives considered**: Separate date_enrollment column — rejected, redundant.

## Decision 4: History rows

- **Decision**: Withdrawal/completion flips the row to terminal state in place; re-enrollment inserts a NEW row (old terminal rows stay as history). Live check = `status = ENROLLED`.
- **Rationale**: Preserves episode history with the same partial-unique mechanism as lab access.
- **Alternatives considered**: Single row flipped back and forth — rejected, destroys history.

## Decision 5: Withdrawal side effect placement

- **Decision**: `EnrollmentUseCases.withdraw` performs the lab release through the lab-access repo within the same UoW/transaction (release lab row if live). No cross-use-case import: both repos are accessed via the UoW inside the enrollment use case.
- **Rationale**: Keeps transaction atomic and avoids use-case→use-case coupling.
- **Alternatives considered**: Domain event + handler — rejected, no event bus exists; direct repo access is simpler with an active consumer.

## Decision 6: No extra fields

- **Decision**: Only `completed_at` beyond the requested columns. Progress/grade/role/notes deferred until a consumer exists.
- **Rationale**: AGENTS.md rule 3 (no placeholder architecture).
