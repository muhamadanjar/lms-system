# Tasks: Course Watch Lab Terminal

- [x] Confirm product behavior and cross-service contract with the user.
- [x] Inspect Dashboard Section authoring, Course Watch terminal hook, LMS Section contract, and console registry lifecycle.
- [x] Write the feature specification and implementation plan.
- [x] Add the Section domain, persistence, mapper, and API contract field with the LAB_TASK invariant.
- [x] Add a reversible migration defaulting existing Sections to terminal disabled.
- [x] Make console slot cleanup session-owner-aware across SSH failure, takeover, and WebSocket close.
- [x] Add regression tests for Section defaults and API updates, migration default/rollback, and rejected-conflict cleanup.
- [x] Run the focused LMS regression suite: 26 passed.
- [x] Add the Section is_preview field, additive migration, and Dashboard authoring/read contract.
- [x] Add regression tests for is_preview defaults, create/update/read mapping, and migration rollback.
- [x] Run focused Section preview and console ownership regression tests: 6 passed.
- [ ] Run formatter/linter/type checks when the repository tools are available; Ruff is absent from the LMS virtual environment.
- [ ] Verify the Dashboard flow with the updated LMS contract and browser interaction states.
