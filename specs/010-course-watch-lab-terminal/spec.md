# Feature Specification: Course Watch Lab Terminal

## Objective

Add an optional embedded terminal to learner Course Watch for Lab Task Sections, backed by the learner's existing Course Lab and LMS console WebSocket.

## Requirements

- A Section has a terminal_enabled boolean that defaults to false and may be true only for LAB_TASK.
- Section create, update, and read contracts preserve terminal_enabled; existing Sections remain disabled after migration.
- Section create, update, and read contracts also preserve is_preview, defaulting to false. Editor preview marks Sections with is_preview=false as unavailable to learner previews while retaining editor access.
- A learner can open the terminal only through an active Course Lab assigned to that learner. The client uses the existing server_id from the Course Lab access response and connects directly to the LMS console WebSocket.
- terminal_enabled controls whether Course Watch offers the embedded terminal. It does not replace server-side learner enrollment and Course Lab access checks.
- CollectTask submission and review remain required for every Lab Task. The terminal only provides shell access to the assigned Lab VPS.
- The server releases a console slot only when the closing WebSocket owns the slot. A rejected conflict connection cannot release the incumbent session.
- The Dashboard opens a WebSocket only while the terminal panel is expanded and closes it when the panel collapses, the Section changes, or Course Watch exits.

## Acceptance Scenarios

1. Creating or updating a non-Lab Section with terminal_enabled=true returns a validation error; changing an enabled Lab Task to another content type disables its terminal.
2. Existing and newly created Sections default to terminal_enabled=false.
3. A terminal-enabled Lab Task returns the flag through the Section read API and remains submit-able through CollectTask.
4. A learner with an active Course Lab can use the existing console contract; a learner without that access is rejected.
5. A second console connection receiving a conflict does not release the first connection's slot.
6. Disconnecting the owner releases its slot, allowing a subsequent connection.
7. Existing and new Sections default to is_preview=false; Section creation, update, and read responses preserve an explicit value.
