# Contracts: Course Lab Access HTTP

**Base**: course-scoped lab router (replaces per-section `/lab` settings + assignment routes).

## GET my lab access

```text
GET /api/courses/{course_slug}/lab/my-lab
Auth: learner JWT
200 ApiResponse[CourseLabAccessRead | null]  meta.resource = "course_lab_access"
404 course not found (code COURSE_NOT_FOUND)
```

Learner without access receives `data: null` (not 404) so UI can show enroll CTA.

## Enroll (one access per user per course)

```text
POST /api/courses/{course_slug}/lab/enroll
Auth: learner (self) or content editor / admin
Body: { "user_id": "u-123" }
201 ApiResponse[CourseLabAccessRead]  meta.resource = "course_lab_access"
409 CAPACITY_EXHAUSTED when no free server (no partial row)
409 DUPLICATE handled idempotently: existing live row returned with 200 on retry path
404 course not found
```

## Release

```text
DELETE /api/courses/{course_slug}/lab/release/{user_id}
Auth: learner (self) or content editor / admin
200 ApiResponse[CourseLabAccessRead]  (released row)
404 when no live access
```

## Removed (breaking, documented)

- `GET/PUT/DELETE /api/courses/{c}/modules/{m}/sections/{s}/lab` (settings) → `404` with `LAB_SETTINGS_REMOVED`, message points to section body + `GET my-lab`.
- `GET .../lab/my-assignment`, `GET .../lab/assignments` → removed; course editors use `GET /api/courses/{slug}/lab/accesses` (optional P2, paginated) — out of MVP unless needed by existing callers.

## Errors (consistent envelope)

```text
{ "data": null, "error": { "code": "CAPACITY_EXHAUSTED | COURSE_NOT_FOUND | LAB_ACCESS_NOT_FOUND | FORBIDDEN", "message": "..." }, "meta": {...} }
```

No credential, secret-ref, or traceback in `message`. `server_id` is returned (opaque UUID) but never accompanied by host/username/secret.
