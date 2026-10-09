# Feature Specification: Actor-Separated LMS API

**Feature Branch**: `011-actor-separated-api`

**Created**: 2026-10-08

**Status**: Draft

**Input**: Separate LMS endpoints and API documentation groups so learners and administrators can quickly identify which API to use.

## User Scenarios & Testing

### User Story 1 - Learner finds learner APIs (Priority: P1)

As a learner or client developer, I can identify the learner-facing API operations from their URL prefix and documentation group, so I can use learning, enrollment, progress, assessment, task, and lab operations without confusing them with content administration.

**Why this priority**: The primary user value is reducing ambiguity about which endpoints learners should use.

**Independent Test**: Inspect the generated API documentation and complete a learner flow using only learner-prefixed endpoints: discover published courses, read accessible content, and use the learner's own enrollment and learning activities.

**Acceptance Scenarios**:

1. **Given** an authenticated learner browsing the API documentation, **When** they look for a learner operation, **Then** its canonical path starts with `/api/learner/` and its group name starts with `Learner`.
2. **Given** an enrolled learner, **When** they read course content or use their own progress, quiz, task, or lab operations through canonical learner routes, **Then** existing publication, enrollment, progression, ownership, and response behavior is preserved.
3. **Given** a learner, **When** they inspect course, module, section, quiz, enrollment, task, file, or lab groups, **Then** learner operations are distinguishable from their administrator counterparts.

### User Story 2 - Administrator finds administration APIs (Priority: P1)

As an administrator, instructor, or client developer, I can identify content-management and administrative operations from their URL prefix and documentation group, so I can author and manage LMS data without confusing those operations with learner activities.

**Why this priority**: Administration operations include draft and archived content, learner management, review workflows, and protected lab configuration.

**Independent Test**: Inspect the API documentation and complete representative content-authoring, enrollment-management, task-review, and server-management operations using administrator-prefixed endpoints.

**Acceptance Scenarios**:

1. **Given** an authorized content editor, **When** they inspect canonical administration routes, **Then** each route starts with `/api/admin/` and is listed in a group starting with `Admin`.
2. **Given** an authorized administrator or instructor, **When** they use administration routes, **Then** current authorization rules and access to draft or archived content are preserved.
3. **Given** a learner, **When** they call an administrator-only authoring, enrollment-management, task-review, or server-management operation, **Then** the existing authorization policy denies the operation.

### User Story 3 - Existing clients migrate without interruption (Priority: P2)

As a client that still calls an existing LMS endpoint, I can continue using the old contract while migrating to the actor-specific API, so the endpoint organization can improve without an immediate client outage.

**Why this priority**: Dashboard and other clients may still use the current shared paths while canonical paths are introduced.

**Independent Test**: Call representative existing paths and verify their request, response, status, and authorization behavior remain available while the API documentation directs new integrations to the actor-specific routes.

**Acceptance Scenarios**:

1. **Given** an existing client using a legacy path, **When** it sends a request during the compatibility period, **Then** the existing path and behavior remain available.
2. **Given** a developer browsing API documentation, **When** they encounter a legacy route, **Then** it appears under `Legacy Compatibility` and is marked deprecated, while the canonical actor-specific route appears in its role group.
3. **Given** the compatibility period is still active, **When** an old route is called, **Then** it delegates to the same application behavior and does not create a second domain policy.

## Edge Cases

- A role may be allowed to perform a learner self-service operation under current policy; the actor prefix communicates the operation's intended client and does not silently revoke an existing permission.
- An administrator reading learner-visible content must use the learner contract when acting in a learner workflow; administration reads may include drafts and archived data.
- A learner requesting an unpublished or inaccessible course, module, or section receives the existing not-found or access response without learning whether protected content exists.
- Legacy routes that currently combine administrator and learner behavior remain callable only as compatibility operations and are clearly marked as such in documentation.
- WebSocket console routes do not appear in the REST OpenAPI schema; their canonical and legacy paths must still identify the intended actor in the route map.
- Health and authentication metadata are shared technical operations and do not receive an administrator or learner prefix.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST provide canonical administrator operations under `/api/admin/` and canonical learner operations under `/api/learner/`.
- **FR-002**: The system MUST expose actor-prefixed API documentation groups for the resource areas that have administrator and learner workflows: courses, modules, sections, quizzes, enrollments, collect tasks, files, course labs, and server or console access where applicable.
- **FR-003**: Learner-facing course, module, and section reads MUST retain existing publication, enrollment, and progression rules; learner self-service MUST remain scoped to the authenticated learner.
- **FR-004**: Administrator-facing content authoring, enrollment administration, task review, and server configuration MUST retain current role and permission checks, including editor access to draft and archived content where currently allowed.
- **FR-005**: API group names and canonical route prefixes MUST make the intended actor clear without requiring a caller to infer it from a mixed-purpose route or a failed authorization response.
- **FR-006**: New canonical routes MUST preserve the established request and response schemas, status codes, error translation, and domain side effects unless a previously approved feature specification explicitly defines another behavior.
- **FR-007**: Existing shared routes MUST remain available as a temporary compatibility contract while clients migrate. They MUST be marked deprecated and grouped under `Legacy Compatibility` in REST API documentation.
- **FR-008**: Legacy and canonical routes MUST delegate to the same application use cases and MUST NOT duplicate domain rules in presentation adapters.
- **FR-009**: The compatibility period MUST have no automatic removal date in this feature. Retirement requires a later client-migration review and an explicit API change.
- **FR-010**: Existing secret redaction, answer-key protection, learner ownership checks, and lab authorization MUST apply identically through canonical and legacy routes.
- **FR-011**: This feature MUST NOT introduce a persistence schema migration or rename the existing `sections` resource contract; those changes require separate specification and migration work.
- **FR-012**: The API documentation MUST list all `Admin` groups first, all `Learner` groups second, and `Legacy Compatibility` after both actor groups.

### Key Entities

- **Course, Module, Section, Quiz, Enrollment, CollectTask, File, CourseLabAccess, and Server**: Existing resources exposed through actor-specific API operations. This feature changes route and documentation boundaries, not their persisted data or domain invariants.
- **API Operation Group**: A documentation grouping that identifies whether the canonical operation is intended for administrator or learner use; it does not grant authorization by itself.
- **Legacy Compatibility Operation**: An existing route retained temporarily for clients during migration and identified as deprecated in API documentation.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Every canonical operation in the scoped API areas is listed under exactly one actor-specific group and uses the corresponding `/api/admin/` or `/api/learner/` path prefix.
- **SC-002**: No canonical learner operation requires a caller to choose between learner and administrator behavior on the same path and method.
- **SC-003**: Every retained legacy REST operation is grouped as `Legacy Compatibility`, marked deprecated, and remains callable during the migration period.
- **SC-004**: Existing request and response contracts and authorization outcomes remain equivalent between legacy operations and their canonical replacements.
- **SC-005**: Learner APIs continue to expose only the published content and learner-owned data permitted by current course, enrollment, progression, and ownership rules.
- **SC-006**: The generated OpenAPI tag order is Admin groups, Learner groups, then `Legacy Compatibility`.

## Assumptions

- `Admin` includes the existing administrator and instructor/content-editor policies; server operations retain their existing `servers.*` permissions.
- `Learner` identifies the intended consumer group. It does not create a new role or alter current authorization decisions.
- Existing learner enrollment operations remain a learner group; administrator enrollment management receives a clearly labeled administrator group.
- Route suffixes and resource names remain compatible with current contracts where practical; `Section` HTTP paths remain in place during the canonical Chapter transition.
- This feature changes the LMS API and its documentation. External clients can migrate separately while legacy routes remain available.
- Existing health, authentication metadata, and unrelated shared technical operations remain outside the actor-specific groups.
