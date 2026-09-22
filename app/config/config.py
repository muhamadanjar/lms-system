from pydantic_settings import BaseSettings
from pydantic import Field, model_validator
from functools import lru_cache
from .cors import CORSSettings
from .database import DatabaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "LMS"

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    cors: CORSSettings = Field(default_factory=CORSSettings)


@lru_cache
def get_settings() -> Settings:
    return Settings()
