<!--
Sync Impact Report
==================
Version change: unversioned scaffold -> 1.0.0
Modified principles:
- PRINCIPLE_1_NAME -> I. Domain-Driven Learning Model
- PRINCIPLE_2_NAME -> II. Clean Architecture and Dependency Direction
- PRINCIPLE_3_NAME -> III. Explicit Ports, Adapters, and Package Discipline
- PRINCIPLE_4_NAME -> IV. Testable Learning Workflows
- PRINCIPLE_5_NAME -> V. Security, Observability, and Operational Safety
Added sections:
- Architecture and Domain Constraints
- Development Workflow and Quality Gates
Removed sections: None
Follow-up TODOs:
- TODO(RATIFICATION_DATE): Confirm the original adoption date with the project owner.
Deferred non-governance intents:
- Update AGENTS.md with the complete LMS feature coverage and architecture guidance.
- Create or refactor the application folder structure and implement the Clean Architecture/DDD design.
-->

# LMS System Constitution

## Core Principles

### I. Domain-Driven Learning Model

The system MUST model the LMS domain explicitly and use its ubiquitous language in code,
API contracts, persistence mappings, and documentation. A Course contains ordered Modules;
a Module contains ordered Chapters; a Chapter represents one learning activity and MUST be
one of the supported content types: text material, lab quiz, or knowledge quiz. A lab quiz
MUST express instructions and a reproducible lab/VPS configuration; a knowledge quiz MUST
support multiple-choice options and MUST allow one or more correct answers according to its
configuration. Domain invariants, ordering rules, answer validation, and publication rules
MUST live in domain objects or domain services rather than in controllers or ORM models.
This keeps the product behavior understandable and prevents storage concerns from becoming
the domain model.

### II. Clean Architecture and Dependency Direction

The codebase MUST follow Clean Architecture with DDD boundaries: presentation depends on
application use cases, application depends on domain abstractions, and infrastructure
implements those abstractions. Domain code MUST NOT import FastAPI, SQLAlchemy/SQLModel,
Pydantic transport schemas, VPS providers, or other infrastructure concerns. Dependencies
MUST point inward; cross-layer access MUST occur through explicit ports, commands, queries,
repositories, and domain services. Each module, class, and folder MUST have a real
responsibility and at least one active consumer; speculative or unused abstractions MUST
not be introduced. This preserves replaceability of persistence, delivery mechanisms, and
lab providers while keeping business rules independently testable.

### III. Explicit Ports, Adapters, and Package Discipline

External capabilities MUST be represented by narrow interfaces owned by the inner layer.
Python's `abc.ABC`/`@abstractmethod` or `typing.Protocol` MUST be used when a stable port
needs multiple implementations, such as course repositories, lab/VPS provisioning,
quiz evaluation, clock, identity, or event publishing. FastAPI routers, Pydantic models,
SQLAlchemy/SQLModel mappings, and provider clients MUST remain adapters at the boundary.
The project MUST prefer the standard library and the existing locked dependencies before
adding a package. Every dependency MUST have a stated use, version policy, and consuming
module; packages MUST be removed when no production or test code uses them. This prevents
an architecture that is clean on paper but filled with dead wrappers and unused libraries.

### IV. Testable Learning Workflows

Every use case MUST have tests for its success path, domain invariants, authorization
boundary, and relevant failure paths. Domain tests MUST run without a database, web server,
network, or real VPS. Application tests MUST use fake or in-memory ports. Adapter tests MUST
cover persistence mappings and external contracts, and API tests MUST cover request/response
schemas and error translation. Changes to course, module, chapter, lab configuration,
quiz answer evaluation, publication, or ordering behavior MUST include regression tests;
the test suite MUST verify that a multi-answer quiz cannot be evaluated as single-answer
by accident and that lab execution never receives an unvalidated configuration.

### V. Security, Observability, and Operational Safety

The system MUST treat course authoring, publication, quiz answers, lab/VPS settings, and
learner results as protected data. Authorization MUST be enforced in application use cases,
secrets MUST come from configuration or a secret manager, and credentials or sensitive lab
details MUST NOT appear in logs, API errors, fixtures, or repository history. Lab/VPS
provisioning MUST validate target, image, credentials, network, limits, and lifecycle
before execution and MUST support safe failure and cleanup. Public operations MUST emit
structured logs with request or correlation identifiers, actionable error codes, and
metrics for failures and external-provider latency. These rules make learning workflows
auditable without exposing infrastructure or learner data.

## Architecture and Domain Constraints

The canonical bounded context is Learning Content and Assessment, with the following
conceptual ownership:

- Course owns course metadata, lifecycle, and module ordering.
- Module owns a coherent grouping of chapters and chapter ordering within a course.
- Chapter owns common identity, title, position, availability, and content-type selection.
- Text Material owns readable learning content and its publication validation.
- Knowledge Quiz owns questions, options, answer cardinality, scoring, and attempt rules.
- Lab Quiz owns task instructions, validation criteria, and a Lab Environment Specification.
- Lab Environment Specification describes the requested VPS/lab image, resources, access
  mode, network constraints, timeout, and cleanup policy; it does not contain provider
  implementation details.

The implementation MUST keep these concepts cohesive. A repository or service MUST NOT
combine unrelated responsibilities merely to reduce file count. API schemas, ORM models,
domain entities, value objects, and integration DTOs MUST be distinct whenever their
lifecycle or invariants differ. A proposed folder or package MUST map to an owned concept,
use case, adapter, or cross-cutting concern and MUST be deleted or merged if it has no
active responsibility.

## Development Workflow and Quality Gates

Feature work MUST begin with a written specification of user-visible behavior and domain
invariants, followed by an implementation plan and dependency-ordered tasks. Pull requests
MUST identify affected bounded contexts, dependency-direction changes, migrations, security
implications, and test coverage. The following gates are mandatory before merge:

1. Formatting, linting, type checking, and import validation pass.
2. Unit, application, adapter, and API tests relevant to the change pass.
3. Integration tests pass for database, lab/VPS, or other external contracts that changed.
4. Database migrations are reversible or include a documented recovery procedure.
5. Architecture review confirms that new dependencies point inward and every introduced
   abstraction has an active implementation and consumer.
6. Operational changes document logs, metrics, failure behavior, and secret handling.

Breaking changes to API contracts, quiz evaluation semantics, lab configuration semantics,
or persisted domain data MUST include a migration or compatibility plan and explicit release
notes. A change MUST be rejected when it bypasses a use case, embeds domain rules in an
adapter, or leaves a newly introduced package, folder, interface, or method unused.

## Governance

This constitution is the highest-level engineering agreement for the LMS System. When an
existing implementation conflicts with it, the conflict MUST be documented in the feature
plan and resolved through an explicit migration task; convenience alone is not a waiver.

Amendments MUST describe the affected principles, compatibility impact, migration or rollout
needs, and validation evidence. The amendment MUST update the Sync Impact Report, increment
the semantic version, and update the last-amended date. A MAJOR version removes or changes
the meaning of a principle; a MINOR version adds a principle or materially expands required
architecture, security, or workflow rules; a PATCH version clarifies wording without changing
the obligation. Every pull request MUST include a constitution-compliance check, and reviewers
MUST verify domain boundaries, dependency direction, test coverage, and operational safety.

The project owner MUST replace `TODO(RATIFICATION_DATE)` with the actual adoption date when
known. Until then, the missing date is the only accepted governance TODO in this document.

**Version**: 1.0.0 | **Ratified**: TODO(RATIFICATION_DATE): Confirm the original adoption date | **Last Amended**: 2026-09-22
