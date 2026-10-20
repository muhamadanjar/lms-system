"""Configuration for private local and S3-compatible file storage."""

from typing import Literal

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class FileStorageSettings(BaseSettings):
    backend: Literal["local", "s3"] = Field(default="local", validation_alias=AliasChoices("FILE_STORAGE_BACKEND", "BACKEND"))
    local_root: str = Field(default="var/private-files", validation_alias=AliasChoices("FILE_STORAGE_LOCAL_ROOT", "LOCAL_ROOT"))
    bucket: str | None = Field(default=None, validation_alias=AliasChoices("FILE_STORAGE_BUCKET", "BUCKET"))
    region: str = Field(default="us-east-1", validation_alias=AliasChoices("FILE_STORAGE_REGION", "REGION"))
    endpoint_url: str | None = Field(default=None, validation_alias=AliasChoices("FILE_STORAGE_ENDPOINT_URL", "ENDPOINT_URL"))
    access_key_id: SecretStr | None = Field(default=None, validation_alias=AliasChoices("FILE_STORAGE_ACCESS_KEY_ID", "ACCESS_KEY_ID"))
    secret_access_key: SecretStr | None = Field(default=None, validation_alias=AliasChoices("FILE_STORAGE_SECRET_ACCESS_KEY", "SECRET_ACCESS_KEY"))

    model_config = SettingsConfigDict(env_nested_delimiter="__", extra="ignore", case_sensitive=False, populate_by_name=True)
