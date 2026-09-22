# HTTP Contract: Course, Module, and Section CRUD

The persistence slice exposes authoring and learner-read endpoints under `/api`. No version
prefix is used. Routers call application use cases and never access SQLModel sessions directly.

## Authentication

Every endpoint requires a Bearer token. LMS forwards the `Authorization` header to:

```text
GET http://localhost:8070/auth/info
```

The User Management response is expected to contain `id`, optional `email`, `roles`, and
`permissions`. `admin` and `instructor` can author content. Other authenticated users can read
published content. Authentication service rejection returns `401`; an unavailable auth service
returns `503`; insufficient roles return `403`.

## Routes

| Method | Route | Access | Purpose |
|---|---|---|---|
| GET | `/api/courses` | authenticated | Paginated Course list |
| POST | `/api/courses` | admin/instructor | Create Course |
| GET | `/api/courses/{course_slug}` | authenticated | Read Course hierarchy |
| PATCH | `/api/courses/{course_slug}` | admin/instructor | Partial Course update |
| DELETE | `/api/courses/{course_slug}` | admin/instructor | Hard-delete Course hierarchy |
| GET | `/api/courses/{course_slug}/modules` | authenticated | Paginated Module list |
| POST | `/api/courses/{course_slug}/modules` | admin/instructor | Create Module |
| GET | `/api/courses/{course_slug}/modules/{module_slug}` | authenticated | Read Module and Sections |
| PATCH | `/api/courses/{course_slug}/modules/{module_slug}` | admin/instructor | Partial Module update |
| DELETE | `/api/courses/{course_slug}/modules/{module_slug}` | admin/instructor | Hard-delete Module descendants |
| PUT | `/api/courses/{course_slug}/modules/order` | admin/instructor | Atomic Module reorder |
| GET | `/api/courses/{course_slug}/modules/{module_slug}/sections` | authenticated | Paginated Section list |
| POST | `/api/courses/{course_slug}/modules/{module_slug}/sections` | admin/instructor | Create Section |
| GET | `/api/courses/{course_slug}/modules/{module_slug}/sections/{section_slug}` | authenticated | Read Section |
| PATCH | `/api/courses/{course_slug}/modules/{module_slug}/sections/{section_slug}` | admin/instructor | Partial Section update |
| DELETE | `/api/courses/{course_slug}/modules/{module_slug}/sections/{section_slug}` | admin/instructor | Hard-delete Section |
| PUT | `/api/courses/{course_slug}/modules/{module_slug}/sections/order` | admin/instructor | Atomic Section reorder |

## Query and mutation rules

- List endpoints accept `page`, `page_size` (maximum 100), `status`, and `include_archived`.
- Learners are forced to `status=PUBLISHED` and cannot include archived content.
- Slugs are required, globally unique, lowercase, and immutable.
- `position` is changed only through the dedicated `PUT .../order` endpoint.
- Section `content_type` is immutable after creation; Lab and Quiz detail resources are managed
  separately from the Section CRUD endpoint.
- `DELETE` is hard delete. Archiving uses `PATCH` with `status=ARCHIVED`.
- Parent ownership is checked from the URL hierarchy; a Module or Section cannot be addressed
  through another parent.

## Response and errors

Success responses use:

```json
{
  "data": {},
  "meta": {}
}
```

List responses include `page`, `page_size`, and `total` in `meta`. Errors use:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "course not found",
    "request_id": "optional-request-id"
  }
}
```

Expected status classes are `401`, `403`, `404`, `409`, `422`, and `503`.

Learner-facing content responses never include VPS credentials, resolved secrets, private keys,
or quiz answer keys.
