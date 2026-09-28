# Data Model: Course Lab Access

**Feature**: specs/004-course-lab-access/spec.md | **Plan**: specs/004-course-lab-access/plan.md

## Entities

### CourseLabAccess (NEW aggregate-adjacent entity, replaces LabAssignment)

- Identity: `id: UUID`
- Owner: `user_id: str` (opaque learner id from identity provider, stripped non-empty)
- Scope: `course_id: UUID` (FK `courses.id`, immutable after creation)
- Binding: `server_id: UUID` (FK `remote_servers.id`, nullable only transiently during creation; live rows MUST hold a server)
- State: `state: ACTIVE | RELEASED` (no QUEUED)
- Audit: `created_at, updated_at: datetime (tz-aware UTC)`

**Invariants**:

- `user_id` required, non-blank; `course_id` required.
- Exactly one live (`state = ACTIVE`) row per `(user_id, course_id)` — enforced by partial unique index `uq_course_lab_access_user_course_live WHERE state = 'ACTIVE'` (Postgres) / equivalent filtered index (SQLite).
- One live holder per server — partial unique index `uq_course_lab_access_server_active WHERE state = 'ACTIVE'` on `server_id`.
- `ACTIVE` requires non-null `server_id`; `RELEASED` clears `server_id` to NULL and never returns to `ACTIVE` (re-enroll creates a new row or re-activates per repository rule below — chosen: new row, preserving history).
- `(user_id, course_id)` pair is immutable; `server_id` changes only via `release()` (clear) — no silent reassignment.

**State transitions**: `ACTIVE --release()--> RELEASED` (terminal). No re-activation of the same row.

### VPS Endpoint — `remote_servers` (UNCHANGED, inventory owned by admin)

- Consumed via existing `RemoteServerRepository`: `free = servers where deleted_at IS NULL and id NOT IN (select server_id from course_lab_access where state='ACTIVE')`.
- Deleting a server sets assigned live accesses to `server_id = NULL`? NO — FK is `ON DELETE SET NULL` but live invariant requires server; therefore repository MUST treat `server_id IS NULL + ACTIVE` as broken and console MUST refuse with maintenance error. Preferred admin flow is soft-delete (`deleted_at`) which keeps FK intact while excluding from `free`.

### Lab Section Content (NO new table)

- Task instructions are the existing `sections.body` for rows with `content_type = LAB_TASK`. No spec columns, no settings table, no per-section lab state.

## Tables

### `course_lab_access` (NEW)

```text
id UUID PK
user_id VARCHAR(255) NOT NULL INDEX
course_id UUID NOT NULL FK courses.id ON DELETE CASCADE INDEX
server_id UUID NULL FK remote_servers.id ON DELETE SET NULL INDEX
state VARCHAR(8) NOT NULL DEFAULT 'ACTIVE' INDEX  -- ACTIVE | RELEASED
created_at TIMESTAMPTZ NOT NULL
updated_at TIMESTAMPTZ NOT NULL
UNIQUE (user_id, course_id) WHERE state = 'ACTIVE'   -- live scope
UNIQUE (server_id) WHERE state = 'ACTIVE'            -- exclusive holder
```

### Dropped

- `lab_environment_settings` (all columns incl. provider/region/image/cpu/memory_mb/storage_gb/access_method/username/secrets/network_policy/timeout/cleanup_policy) — no replacement.
- `lab_assignments` incl. `section_id`, `QUEUED` semantics, `queue_position` helper, `uq_lab_assignments_user_section_live`, `uq_lab_assignments_server_active`.

## Migration `0008_course_lab_access` (irreversible data)

1. Create `course_lab_access` + indexes as above.
2. Backfill: for each distinct `(user_id, course)` reachable from legacy `lab_assignments JOIN sections JOIN modules` where legacy `state <> 'RELEASED'`, insert one `ACTIVE` row picking `ORDER BY (state='ACTIVE') DESC, updated_at DESC LIMIT 1` mapped to its `server_id` (must be non-null; skip server-null QUEUED rows unless no ACTIVE exists — then skip group and leave unenrolled, since server-less access is invalid in the new model).
3. Drop legacy partial indexes, then `lab_assignments`, then `lab_environment_settings` (+ its slug reservations in `content_slugs` where `content_type='lab_environment_settings'` if present).
4. Downgrade recreates empty legacy tables for schema rollback only; backfilled/dropped data is NOT restored (documented in quickstart + release notes).

## Repository port (`CourseLabAccessRepository`)

```text
create(access) -> access            # raises Conflict on duplicate live (user,course) or taken server
get_live(user_id, course_id) -> access | None
list_live_by_course(course_id) -> list[access]
list_live_by_user(user_id) -> list[access]
find_active_by_server(server_id) -> access | None
free_server_ids(limit) -> list[server_id]
update(access) -> access            # release path only; owner+course immutable
```

## API DTO (`CourseLabAccessRead`)

`{ id, user_id, course_id, server_id, state, created_at, updated_at }` — no `section_id`, no `queue_position`, no credential fields.
