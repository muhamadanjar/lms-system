# Contracts: Course Enrollment HTTP

**Router**: `presentation/routers/enrollments.py`, prefix `/api/courses/{course_slug}/enrollments`.

## Enroll

```text
POST /api/courses/{course_slug}/enrollments
Auth: self (user_id == self) or admin/instructor
Body: { "user_id": "u-123", "enrolled_at": "2026-01-05T00:00:00Z" optional, admin-only }
201 ApiResponse[EnrollmentRead]  meta.resource = "enrollment"
200 ApiResponse[EnrollmentRead]  idempotent retry returns existing live row
404 course not found (COURSE_NOT_FOUND)
403 enroll other user as learner (FORBIDDEN)
```

`enrolled_at` supplied by non-editor is ignored (server time used).

## My enrollment

```text
GET /api/courses/{course_slug}/enrollments/me
Auth: learner JWT
200 ApiResponse[EnrollmentRead | null]  meta.resource = "enrollment"
```

`data: null` when no live enrollment (UI shows enroll CTA).

## List (editors)

```text
GET /api/courses/{course_slug}/enrollments?status=ENROLLED
Auth: admin/instructor
200 ApiResponse[list[EnrollmentRead]]
```

## Complete

```text
POST /api/courses/{course_slug}/enrollments/{user_id}/complete
Auth: admin/instructor (or self? NO — editors only)
Body: { "completed_at": "..." optional, default now }
200 ApiResponse[EnrollmentRead] with status COMPLETED
404 no live enrollment
```

## Withdraw

```text
POST /api/courses/{course_slug}/enrollments/{user_id}/withdraw
Auth: self or admin/instructor
200 ApiResponse[EnrollmentRead] with status WITHDRAWN (+ lab access released)
404 no live enrollment
```

## Lab gate (changed behavior, documented)

```text
POST /api/courses/{slug}/lab/enroll without live enrollment
→ 403 { code: ENROLLMENT_REQUIRED, message: "Enrollment in this course is required" }
```

## Errors

```text
{ "data": null, "error": { "code": "ENROLLMENT_REQUIRED | COURSE_NOT_FOUND | ENROLLMENT_NOT_FOUND | FORBIDDEN", "message": "..." }, "meta": {...} }
```
