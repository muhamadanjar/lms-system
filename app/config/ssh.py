from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class SSHConsoleSettings(BaseSettings):
    """
    SSH console + credential encryption settings.
    Nested env: SSH__CREDENTIAL_ENC_KEY ; legacy flat: SSH_CREDENTIAL_ENC_KEY
    """

    credential_enc_key: str = Field(
        default="",
        validation_alias=AliasChoices("ssh__credential_enc_key", "SSH_CREDENTIAL_ENC_KEY"),
    )
    credential_key_version: int = Field(
        default=1,
        validation_alias=AliasChoices("ssh__credential_key_version", "SSH_CREDENTIAL_KEY_VERSION"),
    )
    connect_timeout: float = Field(
        default=15.0,
        validation_alias=AliasChoices("ssh__connect_timeout", "SSH_CONNECT_TIMEOUT"),
    )
    auth_timeout: float = Field(
        default=15.0,
        validation_alias=AliasChoices("ssh__auth_timeout", "SSH_AUTH_TIMEOUT"),
    )
    ping_interval_seconds: float = Field(
        default=30.0,
        validation_alias=AliasChoices("ssh__ping_interval_seconds", "SSH_PING_INTERVAL_SECONDS"),
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    @field_validator("credential_enc_key")
    @classmethod
    def non_empty(cls, value: str) -> str:
        if not value:
            raise ValueError("SSH_CREDENTIAL_ENC_KEY must be set (base64 of 32 bytes)")
        return value