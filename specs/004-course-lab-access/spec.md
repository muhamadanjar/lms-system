# Feature Specification: Course Lab Access

**Feature Branch**: `004-course-lab-access`

**Created**: 2026-09-28

**Status**: Draft

**Input**: Simplify redundant lab tables. Remove server-spec settings (`lab_environment_settings`). Learner accesses VPS without VPS login (handled by platform), reads task instructions from lab content. VPS setup done by admin/teacher. Each user has exactly 1 VPS access per course, shared across sections in the same course; different course = different access.

**Grill session**: 2026-09-28 — decisions: course-level access, drop settings total, keep server inventory, server-side SSH, auto-assign without queue, course-level API, irreversible migration.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Learner uses one VPS per course (Priority: P1)

As a learner enrolled in a course, I can open my lab workspace for that course from any lab section in the course and use the same VPS, and I can read the task instructions for each section, so that I finish all lab tasks without managing VPS credentials.

**Why this priority**: This is the core simplification — one access per user per course replaces per-section assignments and removes server-spec management from the learner flow.

**Independent Test**: Enroll a learner in a course with two lab sections, open the lab workspace from section A and from section B, verify both open the same VPS workspace and each section shows its own task instructions.

**Acceptance Scenarios**:

1. **Given** a learner enrolled in course C with lab sections S1 and S2, **When** the learner opens the lab from S1 and then from S2, **Then** both show the same VPS workspace for (learner, C).
2. **Given** the same learner, **When** the learner views S1 and S2 content, **Then** each shows its own task instructions while sharing one VPS connection.
3. **Given** a learner enrolled in courses C1 and C2, **When** the learner opens labs in each course, **Then** each course shows a different VPS workspace.
4. **Given** a learner without lab access in a course, **When** the learner tries to open the lab workspace, **Then** access is denied with a clear message.

---

### User Story 2 - Admin/teacher provides VPS access (Priority: P1)

As an admin or teacher, I can provide VPS endpoints and ensure each learner in a course gets one VPS access, so that learners can start working without waiting for per-section setup.

**Why this priority**: Without this, the learner story cannot work — VPS provisioning responsibility moves fully to admin/teacher side.

**Independent Test**: Register two VPS endpoints, enroll two learners in the same course, verify each learner gets a distinct VPS and a second enroll returns the existing access.

**Acceptance Scenarios**:

1. **Given** available VPS endpoints, **When** a learner enrolls in a course with labs, **Then** the learner receives exactly one VPS access for that course.
2. **Given** a learner who already has access in a course, **When** enrollment runs again, **Then** the existing access is returned and no second access is created.
3. **Given** no free VPS endpoint is available, **When** a learner enrolls, **Then** enrollment fails explicitly with a capacity message and no partial access is left behind.
4. **Given** a learner leaves or is released from a course, **When** release runs, **Then** the VPS access for that course is freed for reuse.

---

### User Story 3 - Lab access never exposes credentials (Priority: P1)

As a security-conscious platform, I ensure learners never see VPS passwords or keys and such secrets never appear in responses, logs, or error messages.

**Why this priority**: Removing login from the learner side must not leak credentials through the new course-level path.

**Independent Test**: Create accesses for known secrets, then inspect learner-facing responses, logs, and error surfaces for any occurrence of those secret strings.

**Acceptance Scenarios**:

1. **Given** a learner lab workspace, **When** its details are displayed, **Then** no password, private key, or credential reference value is included.
2. **Given** a failed lab connection, **When** the error is shown or logged, **Then** the message describes the failure without secret material.
3. **Given** two learners sharing no course, **When** one tries to open the other's VPS workspace, **Then** access is denied.

---

### Edge Cases

- What happens when a course has zero lab sections? No lab access is created or required.
- How does system handle a learner with two lab sections in one course requesting access concurrently? Exactly one access row wins; the other request returns the same row.
- How does system handle legacy data with multiple per-section assignments for the same (user, course)? Migration keeps exactly one live access (most recently active), the rest are treated as released.
- What happens when a VPS endpoint is deleted while assigned? The affected course access is marked unusable and the learner sees a maintenance message, not a secret or stack trace.
- What happens when server-spec settings from the old model are still referenced by clients? Old per-section settings endpoints are removed; clients receive a clear not-found/deprecation message with the new course-level path.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST grant at most one live lab access per (user, course) pair.
- **FR-002**: System MUST share the same lab access across all lab sections within the same course for the same user.
- **FR-003**: System MUST isolate lab access by course — access in course A MUST NOT open the VPS of course B.
- **FR-004**: System MUST store lab task instructions as section content readable by enrolled learners, with no separate server-spec settings object.
- **FR-005**: System MUST NOT require learners to enter VPS host, username, password, or key at any point in the lab flow.
- **FR-006**: System MUST NOT include VPS secrets, credential values, or correct-answer material in learner-facing responses, logs, or error messages.
- **FR-007**: System MUST resolve the VPS connection server-side using the stored course access and the requesting learner identity.
- **FR-008**: System MUST fail enrollment explicitly when no free VPS endpoint exists, leaving no partial or duplicate access.
- **FR-009**: System MUST return the existing live access on repeated enrollment for the same (user, course) instead of creating a duplicate.
- **FR-010**: System MUST release all live accesses of a user within a course on release and make the VPS endpoints reusable.
- **FR-011**: System MUST remove server-spec settings management (create/read/update/delete per section) from the learner and authoring flows.
- **FR-012**: System MUST provide a course-level lab access read (my-lab) replacing per-section assignment reads.
- **FR-013**: System MUST migrate legacy per-section assignments to one live access per (user, course), keeping the most recently active one.

### Key Entities

- **Course**: Learning unit that owns lab access scope; one access per learner belongs to exactly one course.
- **Lab Section Content**: Task instructions shown per section; readable text owned by its section, no server specs.
- **CourseLabAccess**: Live mapping of one learner to one VPS endpoint within one course; unique per (user, course).
- **VPS Endpoint (inventory)**: Admin-managed connection target assigned to at most one live course access at a time.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Learners can open their course lab workspace from any lab section in under 1 minute without entering credentials.
- **SC-002**: 100% of learners with multiple lab sections in one course share a single VPS workspace for that course.
- **SC-003**: Zero occurrences of VPS secrets in learner responses, logs, or error messages under secret-scan tests.
- **SC-004**: Repeated enrollment for the same learner and course creates zero duplicate accesses.
- **SC-005**: Removal of server-spec settings reduces lab-related management screens/steps reported by teachers in acceptance review.

## Assumptions

- Learners authenticate with the existing platform identity; no new login mechanism is introduced.
- VPS endpoints are provided and maintained by admin/teacher through the existing server inventory.
- Legacy server-spec settings data is intentionally discarded (irreversible migration accepted 2026-09-28).
- No waiting-queue semantics: capacity exhaustion is an explicit failure, not a queued state.
- Existing interactive console behavior (single active session per server) is preserved and re-scoped to course access checks.
