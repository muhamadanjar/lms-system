# Research: Course Lab Access

**Feature**: specs/004-course-lab-access/spec.md | **Date**: 2026-09-28

All unknowns were resolved in the grill session; this file records the decisions so planning has no NEEDS CLARIFICATION left.

## Decision 1: Course-level access granularity

- **Decision**: One live row per `(user_id, course_id)` → `server_id`. All lab sections in the course share it. Different course = different row.
- **Rationale**: Matches actual usage (one VPS per learner per course) and removes per-section fan-out on enroll/release.
- **Alternatives considered**: Keep per-section with shared server pointer — rejected, preserves N-row bookkeeping and queue complexity with no user value.

## Decision 2: Drop `lab_environment_settings` entirely

- **Decision**: `DROP TABLE lab_environment_settings` plus delete its domain entity, SQLModel table, repository, use cases (`lab_settings.py`, `lab_management.py` secret-resolver if unused), mappers, schemas, routers, and tests.
- **Rationale**: Server specs (provider/image/cpu/memory/storage/timeout/cleanup/network) are never used in this LMS; VPS is supplied by admin inventory. Instructions live in section body.
- **Alternatives considered**: Keep minimal timeout/cleanup columns at course level — rejected, no consumer and reintroduces spec management the grill removed.

## Decision 3: Reuse `remote_servers` inventory, no new provisioning abstraction

- **Decision**: Admin CRUD on `remote_servers` stays the sole supply. Enroll picks a free server (`deleted_at IS NULL` + not held by another live access) and locks it via unique constraint. No `LabProvisioner` implementation is added.
- **Rationale**: No auto-provisioning exists in the codebase path being simplified; adding a provisioner port with one fake would violate the no-placeholder rule.
- **Alternatives considered**: New provision/port pair — rejected, no active consumer.

## Decision 4: No queue; capacity failure is explicit

- **Decision**: Remove `QUEUED` state and `queue_position`. Access is either live (holds server) or absent/released. `free_server_ids(limit)` stays as the finder; enroll raises capacity error when empty. Concurrent double-enroll relies on unique `(user_id, course_id)` + unique active `server_id` to let one winner commit.
- **Rationale**: Grill agreement — queuing per-section VPS access has no user value at course scope.
- **Alternatives considered**: Keep queue at course level — rejected, adds states/endpoints without a requirement.

## Decision 5: Server-side SSH, course-scoped console auth

- **Decision**: Keep `GET /api/v1/servers/{id}/console` behavior (single active session + takeover, asyncssh PTY, AES-GCM ciphertext). Change `user_may_open_console` from `user_has_active_server(user, server)` (section assignment) to course-access check: learner passes iff a live `course_lab_access` row links them to a course whose access holds that `server_id`. Admin/superuser path unchanged.
- **Rationale**: Preserves the proven console slice from `002-remote-server-console` while enforcing course isolation and zero credential exposure.
- **Alternatives considered**: Per-section check + course fallback — rejected, dual rules leak section scoping back in.

## Decision 6: Course-level HTTP surface

- **Decision**: New `presentation/routers/course_labs.py`: `GET /api/courses/{slug}/lab/my-lab`, `POST /api/courses/{slug}/lab/enroll {user_id}`, `DELETE /api/courses/{slug}/lab/release/{user_id}`. Delete per-section `GET/PUT/DELETE /lab` settings and `GET /lab/my-assignment`, `GET /lab/assignments` from `presentation/routers/labs.py` (delete file if nothing remains) plus `enrollments.py` assignment mapping.
- **Rationale**: One read + enroll/release per course matches the domain; section URLs would imply per-section state that no longer exists.
- **Alternatives considered**: Deprecation shim returning course access from section URLs — rejected, prolongs the redundant contract.

## Decision 7: Migration strategy (irreversible by agreement)

- **Decision**: `0008_course_lab_access`: (a) create `course_lab_access` with `course_id FK courses.id ON DELETE CASCADE`, `server_id FK remote_servers.id ON DELETE SET NULL`, unique `(user_id, course_id)` live + unique active `server_id`; (b) backfill one row per (user, course) from legacy `lab_assignments` joined through `sections → modules → courses`, keeping most recently updated `ACTIVE`, else most recent `QUEUED`, mapping `RELEASED`-only groups to nothing; (c) drop legacy indexes/table + `lab_environment_settings` table; (d) no data downgrade (schema downgrade recreates empty tables only, documented).
- **Rationale**: Preserves live learner continuity with a deterministic dedup rule accepted in the grill.
- **Alternatives considered**: Fresh empty table without backfill — rejected, would strand active learners.
