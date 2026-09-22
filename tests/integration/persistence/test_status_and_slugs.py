import pytest

from app.domain.entities.course import Course
from app.domain.exceptions import ConflictError, ValidationError
from app.infrastructure.persistence.unit_of_work import SqlModelUnitOfWork


async def test_slugs_are_global_and_immutable(session):
    first = Course(slug="shared-slug", title="First")
    second = Course(slug="shared-slug", title="Second")
    async with SqlModelUnitOfWork(session=session) as uow:
        await uow.courses.create(first)
        await uow.commit()
    async with SqlModelUnitOfWork(session=session) as uow:
        with pytest.raises(ConflictError):
            await uow.courses.create(second)

    first.slug = "changed"  # type: ignore[misc]
    async with SqlModelUnitOfWork(session=session) as uow:
        with pytest.raises(ValidationError):
            await uow.courses.update(first)
