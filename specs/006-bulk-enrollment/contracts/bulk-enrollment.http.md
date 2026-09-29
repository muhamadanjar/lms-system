# Contracts: Bulk Enrollment HTTP

## Bulk enroll

```text
POST /api/courses/{course_slug}/enrollments/bulk
Auth: admin/instructor/superuser (require_content_editor)
Body: { "users": [{ "user_id": "u-1" }, { "email": "a@x.id" }, ...] }  (1–100 items)
207 ApiResponse[BulkEnrollResponse]  meta.resource = "bulk_enrollment"
422 items empty or > 100 (REQUEST_VALIDATION_ERROR)
403 non-editor (FORBIDDEN)
404 course not found (COURSE_NOT_FOUND)
```

Response:

```text
{
  "data": {
    "enrolled": [EnrollmentRead...],
    "skipped": [{ "identifier": "u-9", "reason": "already_enrolled" }],
    "failed": [{ "identifier": "ghost@x.id", "reason": "NOT_FOUND" }]
  },
  "meta": { "resource": "bulk_enrollment" }
}
```

Failure reasons: `INVALID | NOT_FOUND | AMBIGUOUS | DIRECTORY_UNAVAILABLE`.
Bearer from the incoming request is forwarded to UM for email lookups.
