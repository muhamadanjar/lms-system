from collections.abc import Iterable

from app.domain.exceptions import ValidationError


def validate_unique_positions(items: Iterable[object]) -> None:
    positions = [getattr(item, "position") for item in items]
    if len(positions) != len(set(positions)):
        raise ValidationError("sibling positions must be unique")


def reorder_positions(items: list[object], ordered_ids: list[object]) -> None:
    by_id = {getattr(item, "id"): item for item in items}
    if set(by_id) != set(ordered_ids):
        raise ValidationError("reorder must contain exactly the existing siblings")
    for position, item_id in enumerate(ordered_ids):
        setattr(by_id[item_id], "position", position)
