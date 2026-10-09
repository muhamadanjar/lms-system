from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class UserManagementSettings(BaseSettings):
    base_url: str = Field(
        default="http://localhost:8070",
        validation_alias=AliasChoices("usermanagement__base_url", "USERMANAGEMENT_BASE_URL"),
    )
    auth_info_path: str = Field(
        default="/auth/info",
        validation_alias=AliasChoices("usermanagement__auth_info_path", "USERMANAGEMENT_AUTH_INFO_PATH"),
    )
    timeout_seconds: float = Field(
        default=3.0,
        validation_alias=AliasChoices("usermanagement__timeout_seconds", "USERMANAGEMENT_TIMEOUT_SECONDS"),
    )
    notification_client_id: str = Field(
        default="",
        validation_alias=AliasChoices("usermanagement__notification_client_id", "USERMANAGEMENT_NOTIFICATION_CLIENT_ID"),
    )
    notification_client_secret: SecretStr = Field(
        default=SecretStr(""),
        validation_alias=AliasChoices("usermanagement__notification_client_secret", "USERMANAGEMENT_NOTIFICATION_CLIENT_SECRET"),
    )
    notification_audience: str = Field(
        default="usermanagement-api",
        validation_alias=AliasChoices("usermanagement__notification_audience", "USERMANAGEMENT_NOTIFICATION_AUDIENCE"),
    )
    notification_scope: str = Field(
        default="notifications.publish",
        validation_alias=AliasChoices("usermanagement__notification_scope", "USERMANAGEMENT_NOTIFICATION_SCOPE"),
    )
    oauth_token_path: str = Field(
        default="/oauth/token",
        validation_alias=AliasChoices("usermanagement__oauth_token_path", "USERMANAGEMENT_OAUTH_TOKEN_PATH"),
    )
    notification_publish_path: str = Field(
        default="/internal/v1/notifications",
        validation_alias=AliasChoices("usermanagement__notification_publish_path", "USERMANAGEMENT_NOTIFICATION_PUBLISH_PATH"),
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    @property
    def auth_info_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/{self.auth_info_path.lstrip('/')}"
