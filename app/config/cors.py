from typing import List, Union
from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_comma_list(v: Union[str, list, None]) -> list:
    if v is None:
        return ["*"]
    if isinstance(v, list):
        return v if v else ["*"]
    if isinstance(v, str):
        parts = [x.strip() for x in v.split(",") if x.strip()]
        return parts if parts else ["*"]
    return ["*"]


class CORSSettings(BaseSettings):
    """
    CORS configuration. Supports:
    - Nested: CORS__ALLOWED_ORIGINS
    - Legacy: CORS_ALLOW_ORIGINS, CORS_ALLOW_METHODS, CORS_ALLOW_HEADERS, CORS_ALLOW_CREDENTIALS
    Env string comma-separated (e.g. "http://a.com,http://b.com") di-parse jadi list.
    """

    # Union agar raw string dari env (comma-sep) diterima; validator normalisasi ke List[str]
    allowed_origins: Union[str, List[str]] = Field(
        default=["*"],
        validation_alias=AliasChoices("cors__allowed_origins", "cors_allowed_origins", "cors_allow_origins"),
    )
    allowed_methods: Union[str, List[str]] = Field(
        default=["*"],
        validation_alias=AliasChoices("cors__allowed_methods", "cors_allowed_methods", "cors_allow_methods"),
    )
    allowed_headers: Union[str, List[str]] = Field(
        default=["*"],
        validation_alias=AliasChoices("cors__allowed_headers", "cors_allowed_headers", "cors_allow_headers"),
    )
    allow_credentials: bool = Field(
        default=True,
        validation_alias=AliasChoices("cors__allow_credentials", "cors_allow_credentials", "cors_allowed_credentials"),
    )

    @field_validator("allowed_origins", "allowed_methods", "allowed_headers", mode="before")
    @classmethod
    def parse_list(cls, v: Union[str, list, None]) -> list:
        return _parse_comma_list(v)
