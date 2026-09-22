# Repository and Application Port Contracts

This feature does not expose new public HTTP endpoints. It defines internal ports used by the
application layer and implemented by SQLModel infrastructure adapters.

## `CourseRepository`

- `create(course) -> Course`
- `get_by_id(course_id) -> Course | None`
- `get_by_slug(slug) -> Course | None`
- `get_hierarchy(course_id, include_archived=False) -> CourseHierarchy`
- `update(course) -> Course`
- `delete(course_id) -> bool`

`get_hierarchy` returns Modules and Sections ordered by `position, id`. `delete` performs the
specified hard cascade and removes the matching slug registry entries in the same unit of work.

## `ModuleRepository`

- `create(module) -> Module`
- `get_by_id(module_id) -> Module | None`
- `list_by_course(course_id, include_archived=False) -> list[Module]`
- `update(module) -> Module`
- `delete(module_id) -> bool`

Implementations MUST reject a missing Course and enforce unique position within Course.

## `SectionRepository`

- `create(section) -> Section`
- `get_by_id(section_id) -> Section | None`
- `list_by_module(module_id, include_archived=False) -> list[Section]`
- `update(section) -> Section`
- `delete(section_id) -> bool`

Implementations MUST enforce content-type/detail consistency through the application unit of
work and unique position within Module.

## `ContentSlugRegistry`

- `reserve(slug, content_id, content_kind) -> None`
- `assert_available(slug, excluding_content_id=None) -> None`
- `release(slug, content_id) -> None`

Duplicate slug reservation raises a domain/application conflict. Updating an existing content
record with a different slug is rejected before the persistence adapter is called.

## `UnitOfWork`

```text
async with unit_of_work:
    await course_repository.create(course)
    await module_repository.create(module)
    await section_repository.create(section)
    await unit_of_work.commit()
```

The unit of work owns one database transaction. It MUST roll back all hierarchy, slug registry,
detail-model, and ordering changes when any invariant fails.

## `SecretResolver`

- `resolve(secret_ref) -> SecretValue`

Only the lab provisioning adapter may resolve a secret. Domain entities, repositories, loggers,
HTTP schemas, and learner-facing application responses receive only opaque references or
redacted metadata.
