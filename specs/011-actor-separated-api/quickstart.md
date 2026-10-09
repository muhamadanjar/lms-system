# Quickstart: Actor-Separated LMS API

## Prerequisites

- Run the LMS service with its existing database and authentication configuration.
- Obtain one administrator/instructor JWT and one learner JWT from User Management.
- Use an enrolled learner and a course with published content for learner scenarios.

## Documentation review

1. Open `/docs` or `/openapi.json`.
2. Confirm canonical resource groups are actor-prefixed, including `Admin Courses`, `Learner Courses`, `Admin Quizzes`, `Learner Quizzes`, `Admin Enrollment`, and `Learner Enrollment`.
3. Confirm retained old REST paths are under `Legacy Compatibility` and marked deprecated.
4. Confirm shared health and authentication metadata remain outside the actor groups.

## Learner flow

1. With a learner JWT, list published courses using `GET /api/learner/courses`.
2. Read an enrolled course using `GET /api/learner/courses/{course_slug}`.
3. Read published module and section content and the course progress summary under `/api/learner/courses/...`.
4. Start a quiz sitting and use the learner quiz-sitting routes under `/api/learner/`.
5. Read or submit the learner's own CollectTask and file operations under `/api/learner/`.
6. Request learner lab access and connect to the learner console path only when the learner has active course lab access.

Expected result: current enrollment, publication, progression, ownership, answer-key redaction, and lab access rules remain in force.

## Administrator flow

1. With an administrator/instructor JWT, create or update a Course and its Modules/Sections under `/api/admin/courses/...`.
2. Configure quizzes and author questions under `/api/admin/courses/...`.
3. Manage enrollments under `/api/admin/enrollments` and `/api/admin/courses/.../enrollments`.
4. Review tasks under `/api/admin/collect-tasks` and manage server inventory under `/api/admin/servers`.

Expected result: the current content-editor, review, and `servers.*` permission checks remain in force.

## Compatibility flow

Call one existing path used by a current client. It must remain available, return the established contract, and be documented as deprecated under `Legacy Compatibility` while the canonical route is documented under the actor group.

## Release gates

The project constitution requires HTTP contract regression coverage for authorization and response behavior. Run the repository's relevant contract suite and broader quality gates before release; these validation gates are not executed as part of this authoring step.
