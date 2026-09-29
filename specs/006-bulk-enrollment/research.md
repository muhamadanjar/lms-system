# Research: Bulk Enrollment

**Feature**: specs/006-bulk-enrollment/spec.md | **Date**: 2026-09-28

## Decision 1: UM lookup endpoint

- **Decision**: Use UM `GET /users?search={email}` (verified in UM codebase: route exists, auth required, search tests present).
- **Rationale**: Only user-discovery surface available cross-service; LMS has no local user table by design.
- **Alternatives considered**: New UM endpoint — rejected, out of scope for LMS service.

## Decision 2: Exact-match rule

- **Decision**: Case-insensitive exact equality on `email`; exactly 1 → id; 0 → NOT_FOUND; ≠1 → AMBIGUOUS.
- **Rationale**: Search is substring-based; only exact single match is safe to bind a VPS-gating identity to.
- **Alternatives considered**: First-hit-wins — rejected, misbinding risk.

## Decision 3: Failure isolation

- **Decision**: Single UoW/transaction for the bulk; per-item try/except — resolution failures skip the item, DB conflicts re-check live and mark skipped. UM outage fails email items only.
- **Rationale**: Matches agreed partial-success semantics without N transactions.
- **Alternatives considered**: All-or-nothing — rejected in grill.

## Decision 4: Response code 207

- **Decision**: HTTP 207 Multi-Status with `enrolled/skipped/failed` buckets inside the standard ApiResponse envelope.
- **Rationale**: Mixed per-item outcomes cannot be expressed by 200/201 alone.
- **Alternatives considered**: 200 with overall status field — rejected, less standard.

## Decision 5: user_id precedence

- **Decision**: Entry with both fields uses user_id directly (no lookup call).
- **Rationale**: Explicit id is authoritative; saves a network round trip.
