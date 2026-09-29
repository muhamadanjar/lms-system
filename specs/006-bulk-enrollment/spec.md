# Feature Specification: Bulk Enrollment

**Feature Branch**: `006-bulk-enrollment`

**Created**: 2026-09-28

**Status**: Draft

**Input**: Admin adds multiple participants to a course enrollment at once, identifying each by `user_id` or `email` from User Management.

**Grill session**: 2026-09-28 — decisions: user_id + email accepted; email resolved to canonical user_id via UM `GET /users?search=` (exact case-insensitive single match); per-item 207 results; editor-only, max 100, dedup, blank failed; enrollment only (no auto lab).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Admin bulk-enrolls participants (Priority: P1)

As an admin, I can enroll up to 100 participants in one request using their user_ids or emails, and see per-person what succeeded, what was already enrolled, and what failed with reasons.

**Why this priority**: Single-by-single enrollment does not scale for class onboarding; this is the whole feature.

**Independent Test**: Bulk request with mixed new/existing/invalid entries returns 207 with correct enrolled/skipped/failed buckets.

**Acceptance Scenarios**:

1. **Given** a course and a list of new user_ids, **When** bulk enroll runs, **Then** each gets a live ENROLLED record and all appear in `enrolled`.
2. **Given** some entries already enrolled, **When** bulk enroll runs, **Then** those appear in `skipped` with reason `already_enrolled` and nothing duplicates.
3. **Given** blank identifiers or entries with neither user_id nor email, **When** bulk enroll runs, **Then** those appear in `failed` with reason `INVALID`.
4. **Given** more than 100 entries, **When** bulk enroll runs, **Then** the request is rejected (422) with nothing stored.
5. **Given** a non-editor caller, **When** bulk enroll runs, **Then** it is denied (403).

---

### User Story 2 - Enroll by email via User Management (Priority: P1)

As an admin who only knows participant emails, I can bulk-enroll by email and have each resolved to the canonical user_id.

**Why this priority**: Requested explicitly; admins often hold email lists, not internal ids.

**Independent Test**: Bulk with one exact-match email, one unknown email, one ambiguous email → enrolled / NOT_FOUND / AMBIGUOUS respectively, stored rows keyed by user_id.

**Acceptance Scenarios**:

1. **Given** an email matching exactly one UM user, **When** bulk enroll runs, **Then** the enrollment is stored under that user's canonical id.
2. **Given** an email with no UM match, **When** bulk enroll runs, **Then** the item fails with `NOT_FOUND` and other items still proceed.
3. **Given** an email matching multiple users (or no exact match), **When** bulk enroll runs, **Then** the item fails with `AMBIGUOUS`.
4. **Given** UM unreachable, **When** bulk enroll runs, **Then** email items fail with `DIRECTORY_UNAVAILABLE` while user_id items still proceed.
5. **Given** both user_id and email on one entry, **When** bulk enroll runs, **Then** user_id wins (no lookup performed).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept bulk enrollment of 1–100 entries, each with `user_id` and/or `email`.
- **FR-002**: System MUST resolve emails to canonical user_ids via User Management exact (case-insensitive) single match.
- **FR-003**: System MUST return 207 with `enrolled`, `skipped` (with reason), `failed` (identifier + reason) buckets; partial success persists.
- **FR-004**: System MUST restrict bulk enrollment to admin/instructor/superuser.
- **FR-005**: System MUST deduplicate repeated identifiers within one request (later repeats reported as skipped `duplicate_in_request`).
- **FR-006**: System MUST NOT auto-create lab access during bulk enrollment.
- **FR-007**: System MUST forward the caller's bearer token to User Management for email lookups.

### Key Entities

- **BulkEnrollResult**: Per-request outcome bucketing enrollments, skips, failures.
- **UserDirectory**: Port resolving email → canonical user_id (exact match or typed failure).
- **Enrollment**: Unchanged semantics from 005 (one live per user+course).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Admins enroll a 50-person class in a single request in under 1 minute.
- **SC-002**: 100% of email-enrolled rows are keyed by canonical user_id verifiable against UM.
- **SC-003**: Zero duplicate live enrollments result from repeated or overlapping bulk requests.

## Assumptions

- UM exposes `GET /users?search=` returning user objects with `id` and `email`; response envelope tolerated in both enveloped and bare forms.
- The caller's bearer token is accepted by UM for the lookup endpoint.
