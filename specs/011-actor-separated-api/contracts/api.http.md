# Actor-Separated LMS HTTP Contract

All canonical REST operations retain their existing authentication scheme, request and response schemas, status codes, error mapping, pagination, and domain side effects. Only route ownership and documentation grouping change.

## Canonical route map

| Workflow | Canonical administrator path | Canonical learner path | Documentation groups |
|---|---|---|---|
| Course list and detail | `/api/admin/courses[/{course_slug}]` | `/api/learner/courses[/{course_slug}]` | `Admin Courses`, `Learner Courses` |
| Course authoring | `POST/PATCH/DELETE /api/admin/courses...` | — | `Admin Courses` |
| Course progress | — | `GET /api/learner/courses/{course_slug}/progress` | `Learner Courses` |
| Module list, detail, create, update, delete, order | `/api/admin/courses/{course_slug}/modules...` | `GET /api/learner/courses/{course_slug}/modules[/{module_slug}]` | `Admin Modules`, `Learner Modules` |
| Section list, detail, create, update, delete, order | `/api/admin/courses/{course_slug}/modules/{module_slug}/sections...` | `GET /api/learner/courses/{course_slug}/modules/{module_slug}/sections[/{section_slug}]` | `Admin Sections`, `Learner Sections` |
| Learner text completion | — | `POST /api/learner/courses/{course_slug}/modules/{module_slug}/sections/{section_slug}/complete` | `Learner Sections` |
| Quiz metadata, configuration, question authoring, section link/unlink | `/api/admin/courses/.../quizzes...` and `/api/admin/courses/.../sections/{section_slug}/quiz...` | — | `Admin Quizzes` |
| Quiz sitting start and result summary | — | `/api/learner/courses/{course_slug}/modules/{module_slug}/sections/{section_slug}/quiz/...` | `Learner Quizzes` |
| Sitting content, read, answers, finalization | — | `/api/learner/quiz-sittings/{sitting_id}[...]` | `Learner Quizzes` |
| Self-enrollment and own course enrollment | `/api/admin/courses/{course_slug}/enrollments...` for enrollment on behalf of a learner | `/api/learner/courses/{course_slug}/enrollments...` | `Admin Enrollment`, `Learner Enrollment` |
| All-course enrollment listing | `/api/admin/enrollments` | `/api/learner/enrollments` for the caller's own summary | `Admin Enrollment`, `Learner Enrollment` |
| Lab assignment, release, and access listing | `/api/admin/courses/{course_slug}/lab/...` | `/api/learner/courses/{course_slug}/lab/...` for own access | `Admin Course Labs`, `Learner Course Labs` |
| Task submission, file submission, own task read | — | `/api/learner/courses/{course_slug}/modules/{module_slug}/sections/{section_slug}/collect-task...` | `Learner Collect Tasks` |
| Task review queue and review | `/api/admin/collect-tasks...` | — | `Admin Collect Tasks` |
| Task file download | `/api/admin/files/{file_id}` when administrator policy permits | `/api/learner/files/{file_id}` for the task owner | `Admin Files`, `Learner Files` |
| Server inventory | `/api/admin/servers...` | — | `Admin Servers` |
| Console WebSocket | `/api/admin/servers/{server_id}/console` | `/api/learner/servers/{server_id}/console` | Listed in `docs/api-roles.md`; WebSocket operations are not part of REST OpenAPI tags |

For nested operations, the existing path suffix and HTTP method stay the same after inserting the actor prefix, except the legacy `/api/me/enrollments`, `/api/enrollments`, `/api/quiz-sittings`, `/api/files`, and `/api/v1/servers` roots, which map to the explicit actor roots shown above.

OpenAPI tag order is grouped by actor: all `Admin` groups appear first, followed by all `Learner` groups, then `Legacy Compatibility`.

## Authorization and data visibility

- Administrator Course, Module, Section, Quiz, enrollment, and task-review operations retain the current content-editor or administrator guard. Server inventory retains its existing `servers.*` permissions.
- Learner content reads retain current published-status, enrollment, and sequential-access rules. Course discovery retains its current published listing behavior.
- Learner enrollment, quiz sitting, progress, task, and file operations remain scoped to the authenticated learner and existing ownership rules.
- Lab access and console routes retain current enrollment, active-access, and server permission checks.
- Correct answers, provider credentials, private storage keys, and other learners' submissions remain excluded from learner responses.

## Legacy compatibility

Every old REST operation replaced by a canonical route remains callable during migration, appears under the `Legacy Compatibility` tag, and is marked deprecated. The old WebSocket path remains callable and is marked legacy in `docs/api-roles.md`. No legacy route has an automatic retirement date in this feature.

Legacy operations must produce the same response, status, and authorization result as before and must call the same application use cases as canonical operations.

## Shared operations

Health checks and authentication metadata remain at their current shared paths and do not receive an actor prefix.
