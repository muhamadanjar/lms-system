from pydantic import AliasChoices, Field
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
