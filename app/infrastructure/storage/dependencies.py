"""Composition helper for the configured file storage adapter."""

from functools import lru_cache

from app.config.config import get_settings
from app.infrastructure.storage.file_storage import ConfiguredFileStorage


@lru_cache
def get_file_storage() -> ConfiguredFileStorage:
    return ConfiguredFileStorage(get_settings().file_storage)
