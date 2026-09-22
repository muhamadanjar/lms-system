# Feature Specification: Course Module Section Persistence

**Feature Branch**: `001-course-module-section-persistence`

**Created**: 2026-09-23

**Status**: Draft

**Input**: User description: "buatkan schema persistent database menggunakan sqlmodel untuk kebutuhan awal seperti course, module, section"

## Clarifications

### Session 2026-09-23

- Q: Status apa yang harus tersedia untuk setiap model content seperti Course, Module,
  Section, Materi, Tugas Lab, Tugas Kuis, Question, dan Answer? → A: Semua model content
  menggunakan `DRAFT`, `PUBLISHED`, dan `ARCHIVED`.
- Q: Bagaimana aturan uniqueness dan perubahan slug untuk Course, Module, Section, Material,
  Lab Task, Quiz, Question, dan Answer? → A: Slug global unique untuk semua model dan
  immutable sejak dibuat.
- Q: Bagaimana struktur persistence untuk tipe Section dan quiz? → A: Section tetap menjadi
  tabel utama untuk Material dan Lab Task; Lab Task memiliki relasi ke model pengaturan VPS;
  Quiz menggunakan model Quiz, Question, dan QuizSitting. Question memiliki tipe MULTICHOICE
  atau DIRECT dan bobot yang ditentukan pengajar.
- Q: Bagaimana data opsi pilihan ganda dan jawaban langsung disimpan untuk setiap Question? →
  A: Gunakan child answer rows yang ter-normalisasi; opsi pilihan ganda memiliki text dan
  `is_correct`, sedangkan jawaban langsung memiliki accepted answer/value.
- Q: Bagaimana credential VPS pada `LabEnvironmentSettings` harus disimpan? → A: Simpan
  metadata akses di database dan gunakan secret reference untuk password/private key; raw
  secret tidak disimpan di tabel.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create and Load Learning Hierarchy (Priority: P1)

As a course administrator, I can create a Course with ordered Modules and ordered Sections so
that the initial learning content hierarchy is stored and can be loaded consistently.

**Why this priority**: The hierarchy is the minimum persistent foundation for every later
content type and learner-facing course experience.

**Independent Test**: Create one Course, two Modules, and multiple Sections, then load the
Course and verify the complete hierarchy and ordering without manually repairing relationships.

**Acceptance Scenarios**:

1. **Given** a valid Course payload, **When** it is saved, **Then** the Course receives a
   stable identifier and is retrievable with its metadata and timestamps.
2. **Given** a saved Course, **When** valid Modules and Sections are added, **Then** each child
   references its parent and is returned in ascending position order.
3. **Given** a Course with multiple Modules, **When** the hierarchy is loaded, **Then** the
   response contains only its own Modules and each Module contains only its own Sections.

---

### User Story 2 - Maintain Ordering and Relationships (Priority: P1)

As a course administrator, I can update titles, descriptions, and positions while preserving
parent-child integrity so that the displayed course structure remains predictable.

**Why this priority**: Ordering is part of the learning experience and invalid relationships
would make the stored content unusable.

**Independent Test**: Update a Module and reorder its Sections, then reload the hierarchy and
verify the new order, parent identifiers, and unchanged unrelated records.

**Acceptance Scenarios**:

1. **Given** Sections under one Module, **When** their positions are changed to unique valid
   positions, **Then** subsequent reads return the new deterministic order.
2. **Given** a Module belonging to Course A, **When** a request attempts to attach it to an
   invalid or missing Course, **Then** the operation is rejected without an orphan record.
3. **Given** a Section belonging to Module A, **When** a request attempts to move it using a
   missing Module, **Then** the operation is rejected without changing the existing relation.

---

### User Story 3 - Manage Content Status and Audit Metadata (Priority: P2)

As a course administrator, I can manage the status of each content model and know when records
were created or last changed so that content management remains auditable.

**Why this priority**: A shared status vocabulary makes publication filtering predictable across
Course, Module, Section, and their content-specific models.

**Independent Test**: Create and update each model type, change its status, and verify valid
transitions and timestamp behavior.

**Acceptance Scenarios**:

1. **Given** a newly created content model, **When** it is persisted, **Then** it has status
   `DRAFT` and a creation timestamp.
2. **Given** an existing record, **When** editable metadata changes, **Then** its update
   timestamp changes while its identifier and parent relation remain stable.
3. **Given** a content model in one status, **When** a valid status transition is requested,
   **Then** the new status is persisted and the update timestamp changes.

---

### Edge Cases

- A Course, Module, or Section title is empty, exceeds the supported length, or contains only
  whitespace.
- Two Modules under the same Course use the same position.
- Two Sections under the same Module use the same position.
- A child references a parent that does not exist.
- A child references a parent from a different hierarchy during a move operation.
- A duplicate public identifier, slug, or code is submitted.
- A parent is removed while it still has descendants.
- Removing a Course or Module removes all descendants according to the configured cascade
  policy in one atomic operation.
- Two updates attempt to change the same record or ordering positions concurrently.
- A timestamp is supplied in a non-UTC or invalid format.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST persist Course records with a stable identifier, title, optional
  description, slug, status, creation timestamp, and update timestamp.
- **FR-002**: System MUST persist Module records with a stable identifier, required Course
  relationship, title, optional description, slug, status, position, creation timestamp, and
  update timestamp.
- **FR-003**: System MUST persist Section records with a stable identifier, required Module
  relationship, title, optional description, slug, status, position, creation timestamp, and
  update timestamp.
- **FR-004**: System MUST enforce the Course → Module → Section parent-child relationships
  and MUST prevent orphan Modules or Sections.
- **FR-005**: System MUST enforce unique Module positions within one Course and unique Section
  positions within one Module.
- **FR-006**: System MUST return Modules and Sections in deterministic position order, with a
  stable tie-break rule if ordering data is read during a concurrent update.
- **FR-007**: System MUST validate required text fields, supported length limits, slug format,
  shared status values, and timestamp values before persistence.
- **FR-008**: System MUST maintain creation and last-update timestamps in UTC and MUST NOT
  allow an ordinary update to change the original creation timestamp.
- **FR-009**: System MUST expose a persistence model compatible with the project's SQLModel
  constraint and existing relational database configuration.
- **FR-010**: System MUST provide migration support for creating the initial Course, Module,
  Section, Lab Environment Settings, Quiz, Question, Answer, and QuizSitting tables,
  relationships, constraints, and indexes.
- **FR-011**: System MUST reject invalid parent references and conflicting positions without
  leaving partial hierarchy changes.
- **FR-012**: System MUST hard-delete all descendants when a Course or Module is deleted, and
  the cascade MUST execute atomically so that partial hierarchies are not left behind.
- **FR-013**: System MUST use the shared status values `DRAFT`, `PUBLISHED`, and `ARCHIVED`
  for every persisted content model, including Course, Module, Section, Lab Environment
  Settings, Quiz, Question, Answer, and QuizSitting.
- **FR-014**: System MUST default every newly created content model to `DRAFT` and MUST
  preserve the previous status when a requested transition is invalid.
- **FR-015**: System MUST persist a slug for every content model that is intended to be read
  by users, including Course, Module, Section, Lab Environment Settings, Quiz, Question,
  Answer, and QuizSitting.
- **FR-016**: System MUST enforce global uniqueness of slug values across all persisted content
  models and MUST reject any attempt to change a slug after the record is created.
- **FR-017**: System MUST use Section as the primary table for content hierarchy and MUST
  distinguish `MATERIAL`, `LAB_TASK`, and `QUIZ` through a supported content type.
- **FR-018**: System MUST allow a `LAB_TASK` Section to have its VPS configuration in a
  dedicated Lab Environment Settings model without placing provider-specific fields directly
  in Section.
- **FR-018a**: Lab Environment Settings MUST support username/password and public-key access
  modes. Password and private-key values MUST be represented by secret references and MUST NOT
  be stored as raw values in the persistence database.
- **FR-019**: System MUST relate a `QUIZ` Section to one Quiz model; Quiz MUST own its
  Questions and QuizSittings.
- **FR-020**: System MUST persist Question with a type of `MULTICHOICE` or `DIRECT`, and MUST
  persist an instructor-defined weight used by later quiz evaluation.
- **FR-021**: System MUST persist QuizSitting as a distinct model for a learner's quiz attempt
  or sitting and MUST relate it to exactly one Quiz.
- **FR-022**: System MUST persist normalized child Answer rows for each Question; MULTICHOICE
  answers MUST support option text and `is_correct`, while DIRECT answers MUST support an
  accepted answer/value for later matching.

### Key Entities

- **Course**: The top-level learning container. Key data includes stable identity, title,
  description, slug, status, and audit timestamps.
- **Module**: An ordered learning group owned by exactly one Course. Key data includes parent
  identity, title, description, slug, status, position, and audit timestamps.
- **Section**: An ordered learning unit owned by exactly one Module. Key data includes parent
  identity, title, description, slug, status, position, and audit timestamps. It has one of
  the content types `MATERIAL`, `LAB_TASK`, or `QUIZ`.
- **Lab Environment Settings**: Configuration related to the VPS/lab used by a `LAB_TASK`
  Section. It supports username/password or public-key access, stores non-secret connection
  metadata, and references password/private-key secrets without storing raw values.
- **Quiz**: A quiz model related one-to-one with a `QUIZ` Section and owning Questions and
  QuizSittings.
- **Question**: A model owned by Quiz. Its type is `MULTICHOICE` or `DIRECT`, and it has a
  weight defined by the instructor.
- **Answer**: A model representing an answer or answer option owned by a Question. The exact
  storage is normalized into child rows; multi-choice answers have option text and
  `is_correct`, while direct answers have an accepted answer/value.
- **QuizSitting**: A model representing one learner's quiz sitting or attempt, related to one
  Quiz and storing attempt lifecycle data.
- **Status**: A shared content state with values `DRAFT`, `PUBLISHED`, and `ARCHIVED`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Course administrators can create and reload a three-level Course hierarchy
  with 100% preservation of parent relationships and requested order in acceptance tests.
- **SC-002**: 100% of duplicate-position and invalid-parent attempts are rejected without an
  orphan or partially persisted hierarchy.
- **SC-003**: 100% of persisted records expose stable identity and auditable creation/update
  timestamps in the supported data access flows.
- **SC-004**: The initial persistence change can be applied to an empty database and rolled
  back or recovered using a documented migration procedure.
- **SC-005**: Existing database health and connection behavior remains operational after the
  initial schema is introduced.

## Assumptions

- The feature covers persistence foundations for Course, Module, Section, Lab Environment
  Settings, Quiz, Question, Answer, and QuizSitting. Lab execution, VPS provisioning, quiz
  scoring, enrollment, learner progress, and authoring APIs are out of scope.
- The implementation will use the project's existing SQLModel and relational database stack;
  this is an explicit technical constraint from the request, not a new external dependency.
- Stable identifiers use UUID semantics unless the implementation plan identifies a stronger
  compatibility requirement in the existing database configuration.
- The persisted entity and table use the requested term `Section` for this feature. A future
  rename to the canonical domain term `Chapter` requires an explicit migration.
- Titles are required; descriptions are optional; exact length limits are selected during
  planning from the project's validation conventions.
- Timestamps are stored and compared as UTC-aware values.
- Reads return children ordered by position and then stable identifier.
- Deleting a Course hard-deletes its Modules and Sections; deleting a Module hard-deletes its
  Sections. Each cascade is atomic and is covered by integration tests.
- Every content model uses the shared status values `DRAFT`, `PUBLISHED`, and `ARCHIVED`.
- Slugs are intended for user-readable resource lookup, are globally unique across all content
  models, and cannot change after record creation.
- Lab credential values are stored outside the persistence database and are referenced by
  secret identifiers; logs and response data never expose raw password or private-key values.
- Authentication, authorization roles, and ownership checks are deferred to the application
  use-case feature that consumes this persistence layer.
