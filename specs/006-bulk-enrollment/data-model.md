# Data Model: Bulk Enrollment

**Feature**: specs/006-bulk-enrollment/spec.md | **Plan**: specs/006-bulk-enrollment/plan.md

No table changes. Reuses `enrollments` (005) with its partial unique live index as race guard.

## Application types

### BulkEnrollItem (input)

`{ user_id: str | None, email: str | None }` — at least one required (else `INVALID`); blank strings treated as absent.

### BulkEnrollResult (use-case output)

- `enrolled: list[Enrollment]` — newly created live rows.
- `skipped: list[{ identifier, reason }]` — reason `already_enrolled` (pre-existing live) or `duplicate_in_request` (repeat within the batch).
- `failed: list[{ identifier, reason }]` — reason `INVALID` (no usable identifier), `NOT_FOUND`, `AMBIGUOUS`, `DIRECTORY_UNAVAILABLE`.

`identifier` echoes the entry's user_id if given else its email.

## Port (`UserDirectory`)

```text
find_user_id_by_email(email, authorization) -> str
  raises EmailNotFound | EmailAmbiguous | DirectoryUnavailable
```

## Deduplication key

Normalized per entry: `id:<user_id.strip()>` when user_id present else `email:<email.strip().lower()>`. First occurrence processes; later repeats → skipped `duplicate_in_request`.
