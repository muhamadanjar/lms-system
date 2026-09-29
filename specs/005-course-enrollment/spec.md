# Feature Specification: Course Enrollment

**Feature Branch**: `005-course-enrollment`

**Created**: 2026-09-28

**Status**: Draft

**Input**: Add an enrollment table recording course participants: user_id, status, date_enrollment, course_id, timestamps, plus other fields only if genuinely needed.

**Grill session**: 2026-09-28 — decisions: enrollment gates lab access; 3 statuses; single enrolled_at (backdatable); one live row per (user, course) with per-episode history rows; only extra field completed_at; WITHDRAWN auto-releases lab VPS.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Learner enrolls in a course (Priority: P1)

As a learner, I can enroll myself in a course (or be enrolled by an admin/teacher) so that I become a recorded participant with a clear enrollment date.

**Why this priority**: Without a participant record, the lab gate and all downstream participant logic have nothing to check.

**Independent Test**: Enroll learner U in course C, read back the enrollment, verify status ENROLLED and the enrollment date.

**Acceptance Scenarios**:

1. **Given** course C, **When** learner U enrolls (self or via admin), **Then** exactly one live ENROLLED record exists for (U, C) with an enrollment date.
2. **Given** an existing live enrollment, **When** enrollment runs again for the same (U, C), **Then** the existing record is returned and no duplicate is created.
3. **Given** a learner without permission, **When** they try to enroll someone else, **Then** enrollment is denied.

---

### User Story 2 - Lab access requires enrollment (Priority: P1)

As a learner, I can only receive a lab VPS after I am enrolled, so that VPS resources go to real participants.

**Why this priority**: This is the agreed gate semantics connecting enrollment to the existing course lab access.

**Independent Test**: Request lab access without enrollment (denied), enroll, request again (granted).

**Acceptance Scenarios**:

1. **Given** no live enrollment for (U, C), **When** U requests lab access in C, **Then** the request is denied with a clear enrollment-required message.
2. **Given** a live ENROLLED record, **When** U requests lab access, **Then** access is granted per the course-lab-access rules.
3. **Given** a WITHDRAWN-only history, **When** U requests lab access, **Then** the request is denied until re-enrollment.

---

### User Story 3 - Complete or withdraw with lab side effects (Priority: P2)

As an admin/teacher, I can mark a participant COMPLETED or WITHDRAWN so that learner state stays truthful and VPS resources are freed on withdrawal.

**Why this priority**: Lifecycle completion matters for records; withdrawal must not strand VPS servers.

**Independent Test**: Withdraw a learner holding a lab VPS, verify the VPS becomes free; complete another learner, verify their lab access still opens.

**Acceptance Scenarios**:

1. **Given** an ENROLLED learner holding lab access, **When** they are withdrawn, **Then** their lab access for that course is released and the server becomes reusable.
2. **Given** an ENROLLED learner, **When** they are marked COMPLETED, **Then** the record carries a completion date and their lab access keeps working.
3. **Given** a WITHDRAWN learner, **When** they re-enroll, **Then** a new ENROLLED record is created (history preserved) and lab access can be requested again.

---

### Edge Cases

- What happens when a course is deleted? Its enrollment records are removed (cascade); released lab servers stay in inventory.
- What happens on concurrent double enrollment? Exactly one live record wins; the other request returns it.
- What happens when an admin backdates enrolled_at? The record stores the given date; creation audit time stays in created_at.
- What happens when completion is requested without enrollment? A not-found error, not an implicit enrollment.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST keep at most one live (`ENROLLED`) enrollment per (user, course) pair.
- **FR-002**: System MUST store an enrollment date (`enrolled_at`) defaulting to creation time and backdatable by admin/teacher.
- **FR-003**: System MUST support statuses `ENROLLED`, `COMPLETED`, `WITHDRAWN` with only `ENROLLED` counted as live.
- **FR-004**: System MUST record `completed_at` when an enrollment becomes `COMPLETED` and require it.
- **FR-005**: System MUST return the existing live enrollment on repeated enrollment instead of duplicating.
- **FR-006**: System MUST deny lab access requests without a live enrollment for that (user, course).
- **FR-007**: System MUST release the course lab access when its enrollment becomes `WITHDRAWN`.
- **FR-008**: System MUST create a new record (not flip the old one) when a withdrawn learner re-enrolls.
- **FR-009**: System MUST restrict self-enrollment to self, and allow admin/teacher to enroll, complete, or withdraw any learner.
- **FR-010**: System MUST delete enrollment records when their course is deleted.

### Key Entities

- **Enrollment**: Participant episode linking one learner to one course; unique live per (user, course); carries status, enrollment date, completion date.
- **Course**: Scope owner; deletion cascades to enrollments.
- **CourseLabAccess**: Existing VPS binding; gated by live enrollment, released on withdrawal.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Learners complete self-enrollment in under 1 minute and see their enrollment date.
- **SC-002**: 100% of lab access grants in acceptance tests are preceded by a live enrollment.
- **SC-003**: After withdrawal, the freed VPS is reusable by another learner on the next enrollment.
- **SC-004**: Repeated enrollment for the same learner and course creates zero duplicate live records.

## Assumptions

- Learner identity reuses the existing opaque user_id from User Management; no local users table.
- No roles/progress/grades in this slice; only completion date is stored beyond the requested columns.
- Lab VPS provisioning rules from 004-course-lab-access are unchanged except for the added gate.
