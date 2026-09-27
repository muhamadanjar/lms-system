from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Text
from sqlmodel import Field, SQLModel

from app.domain.value_objects.content import AccessMethod
from app.infrastructure.persistence.models.base import utc_now


class RemoteServer(SQLModel, table=True):
    __tablename__ = "remote_servers"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(max_length=120, unique=True, index=True)
    host: str = Field(max_length=255)
    port: int = Field(default=22)
    username: str = Field(max_length=255)
    access_method: AccessMethod = Field(default=AccessMethod.PASSWORD)
    credential_ciphertext: Optional[str] = Field(default=None, sa_type=Text)
    credential_nonce: Optional[str] = Field(default=None, sa_type=Text)
    credential_key_version: Optional[int] = None
    host_key: Optional[str] = Field(default=None, sa_type=Text)
    deleted_at: Optional[datetime] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)