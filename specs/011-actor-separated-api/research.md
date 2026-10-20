# Research: Actor-Separated LMS API

## Decisions

### Add actor prefixes while preserving current routes

- **Decision**: Canonical administrator routes use `/api/admin/...`; canonical learner routes use `/api/learner/...`. Existing routes stay available during migration.
- **Rationale**: The same Course and Section paths currently support editor and learner reads, while writes and learner activities live in shared routers. Explicit prefixes let clients choose by actor before sending a request.
- **Alternatives considered**: Change OpenAPI tags only; this would not make the URL itself clear. Remove the old routes immediately; this would break current Dashboard or other clients.

### Separate documentation tags by actor

- **Decision**: Use resource tags prefixed with `Admin` or `Learner`, such as `Admin Courses`, `Learner Courses`, `Admin Enrollment`, and `Learner Enrollment`.
- **Rationale**: Tags group operations visibly in OpenAPI and complement the path prefixes. Keep the existing learner-enrollment group naming convention.
- **Alternatives considered**: Keep generic `Courses`, `Quizzes`, and `Enrollments` tags; generic tags do not answer which client should use each operation.

### Mark compatibility operations as deprecated and group them separately

- **Decision**: Retained REST operations use the `Legacy Compatibility` tag and FastAPI's deprecated operation metadata. The existing WebSocket path is identified as legacy in the route map because WebSockets are not listed in OpenAPI.
- **Rationale**: Existing clients retain a visible contract, while new clients are directed to canonical actor groups.
- **Alternatives considered**: Hide old operations from OpenAPI; this removes discoverability for client migration. Leave them in generic tags; this preserves the original ambiguity.

### Preserve authorization and domain behavior

- **Decision**: The split is presentation-only. Existing use cases, request/response schemas, status codes, error behavior, and role/permission rules remain authoritative.
- **Rationale**: The user requested clearer endpoint ownership, not new course publication, learner ownership, enrollment, lab, or quiz policy.
- **Alternatives considered**: Use the new path split to tighten role policy; that would be an independent security/API behavior change and would violate the agreed compatibility scope.

### No data migration or Section rename

- **Decision**: No database migration is required. Existing Section route suffixes remain in place.
- **Rationale**: Only endpoint paths and documentation groups change. `sections.py` is transitional compatibility code and a Section-to-Chapter rename requires separate migration planning.
- **Alternatives considered**: Rename `sections` to `chapters` in the same release; this expands the contract change and conflicts with the current compatibility boundary.

## Existing Context

- `specs/008-course-progression-collect-task` defines learner progress and task routes at current prefixes.
- `specs/009-course-watch-learner-contract` defines the learner enrollment summary and quiz sitting content at current prefixes.
- `specs/010-course-watch-lab-terminal` relies on the current learner lab and console authorization behavior.
- The current API role matrix is `docs/api-roles.md`; it describes permission boundaries but currently lists many canonical candidate operations under shared route paths and generic groups.
