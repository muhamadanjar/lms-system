# Data Model: Actor-Separated LMS API

This feature introduces no persisted entity, table, field, enum, or relationship. Course, Module, Section, Quiz, Enrollment, CollectTask, File, CourseLabAccess, and Server data remain unchanged.

## API contract concepts

- **Canonical actor operation**: An existing application operation exposed under an administrator or learner path and documentation group.
- **Legacy compatibility operation**: An existing path retained temporarily, marked deprecated, and mapped to the same application use case as its canonical replacement.

No migration or data backfill is required.
