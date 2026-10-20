# Plan: Lab task review queue

Related Progress: [../../progress/lab-task-review-queue.md](../../progress/lab-task-review-queue.md)

## Goal

Provide one review queue for administrators and instructors. Administrators can
review every course; instructors can review only courses assigned to them.
Keep the CollectTask state machine and return server-paginated queue data with
course, module, section, and latest submission time.

For terminal outcomes, commit the review in LMS and then publish through the
UserManagement internal notification API. UserManagement owns notification
storage and delivery; LMS does not store notifications or maintain a local
notification outbox.

## API

- GET /api/admin/collect-tasks accepts repeated status and learner_id, optional
  course_id and learner_search, and page/per_page.
- With no status filter, return SUBMITTED and IN_REVIEW; callers can request all
  five statuses explicitly.
- Sort by latest SUBMISSION history timestamp ascending, then task ID.
- GET /api/admin/collect-tasks/review-courses returns all courses to admins and
  assigned courses to instructors.
- The backend checks course assignment for both queue reads and review actions.
- GET and DELETE /api/admin/courses/{course_slug}/instructors complete the
  assignment API used by Dashboard.

## Notification delivery

Publish REVISION_REQUIRED, REVIEWED, and PASSED; do not publish IN_REVIEW.
Send the persisted review event UUID as the UserManagement Idempotency-Key.
Keep OAuth credentials server-side and require a provisioned service client
with audience usermanagement-api and scope notifications.publish. Configure
USERMANAGEMENT_NOTIFICATION_CLIENT_ID and
USERMANAGEMENT_NOTIFICATION_CLIENT_SECRET in the LMS environment. The default
notification path is `/internal/v1/notifications`; UserManagement persists the
publication and handles delivery. If that request fails, LMS logs the failure
and keeps the committed review successful; LMS does not retry it locally.

## Persistence

No LMS notification table or Alembic revision is required. The LMS review
transition remains the only persistence operation; UserManagement owns the
notification record after accepting the publish request.
