# Implementation Plan: Course Watch Lab Terminal

## Design

Add a persisted `terminal_enabled` flag to LMS Sections. It defaults to false and can only be enabled for `LAB_TASK`. The LMS Section response carries the flag to Dashboard Course Watch.

Dashboard uses the existing Course Lab access endpoint to obtain the learner's `server_id`, then connects directly to the existing authenticated LMS console WebSocket. The flag controls the Course Watch affordance; the LMS WebSocket continues to enforce learner identity, Enrollment, and active Course Lab ownership.

All Lab Tasks continue to use CollectTask submission and review. No alternate submission path or terminal persistence record is introduced.

Console registry ownership becomes explicit: every release includes the WebSocket session ID. A rejected conflict connection and a failed SSH open may release only the slot acquired by that same connection. Takeover closes and releases the incumbent by its session ID before acquiring a new slot.

## Data and API

- Add `terminal_enabled: bool = false` to the Section domain entity and persistence model.
- Add `is_preview: bool = false` to the Section domain entity and persistence model, and preserve it through mapping and Section create, update, and read contracts.
- Map the field in both persistence directions and preserve it through Section create, update, and read contracts.
- Reject enabling the terminal on non-`LAB_TASK` Sections; clear the flag if an enabled Section changes to another content type.
- Add an additive Alembic migration after `0015_collect_task_files`; existing rows receive false.
- Add a reversible migration after `0016_section_terminal_enabled`; existing rows receive `is_preview=false`.
- Keep the learner console route and Course Lab access response unchanged.

## Console lifecycle

- Change the ConsoleRegistry release contract to require `server_id` and `session_id`.
- Make release conditional on the current slot owner.
- Pass the connection's session ID through SSH failure cleanup, takeover, and WebSocket close cleanup.
- Preserve existing conflict behavior and server-side Course Lab authorization.

## Verification

The LMS repository requires regression coverage for Section API mapping, migration defaults, and console ownership/concurrency. These checks are listed in `tasks.md` and remain a delivery gate. Dashboard browser interaction and cross-service verification also remain required.
