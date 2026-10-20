# Progress: Lab task review queue

Plan: [../../plans/lab-task-review-queue.md](../../plans/lab-task-review-queue.md)

## Status: implementation complete; deployment configuration pending

## Log

- [x] Verify CollectTask state transitions, course instructor persistence, and
      the UserManagement notification contract.
- [x] Initialize this plan and progress record before source changes.
- [x] Add assigned-course scope, paginated queue contract, and instructor
      assignment list/removal APIs in LMS.
- [x] Publish terminal review notifications through UserManagement OAuth
      client credentials after the LMS review transaction commits.
- [x] Remove the LMS notification outbox model, worker, and migration; use the
      persisted review event UUID as UserManagement's idempotency key.
- [x] Refresh the code graph. Runtime delivery and role-scoped behavior still
      require environment-level validation.


Migration: no LMS notification migration is needed. User Management persists
notification publications. The LMS code graph was refreshed.

Deployment still needs a provisioned UserManagement service client and its secret in the LMS environment. Browser, role-scope database, and runtime notification delivery were not runtime-verified here.
