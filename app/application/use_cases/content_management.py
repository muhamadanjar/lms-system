from app.domain.entities.base import ContentEntity
from app.domain.services.content_policy import validate_status_transition
from app.domain.value_objects.content import ContentStatus


def change_status(entity: ContentEntity, target: ContentStatus) -> ContentEntity:
    target = ContentStatus(target)
    validate_status_transition(entity.status, target)
    entity.change_status(target)
    return entity


def assert_immutable_slug(entity: ContentEntity, requested_slug: str) -> None:
    entity.change_slug(requested_slug)
