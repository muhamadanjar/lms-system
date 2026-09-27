from datetime import datetime
from typing import TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.value_objects.content import AccessMethod
from app.domain.value_objects.remote_server import ServerCredential

T = TypeVar("T")


class CredentialInput(BaseModel):
    method: AccessMethod
    password: str | None = None
    public_key: str | None = None
    passphrase: str | None = None

    @model_validator(mode="after")
    def validate_payload(self) -> "CredentialInput":
        if self.method is AccessMethod.PASSWORD:
            if not self.password:
                raise ValueError("password is required for PASSWORD auth")
            if self.public_key or self.passphrase:
                raise ValueError("public_key/passphrase are not valid for PASSWORD auth")
        else:
            if not self.public_key:
                raise ValueError("public_key is required for PUBLIC_KEY auth")
            if self.password:
                raise ValueError("password is not valid for PUBLIC_KEY auth")
        return self

    def to_credential(self) -> ServerCredential:
        if self.method is AccessMethod.PASSWORD:
            return ServerCredential(method=self.method, value=self.password or "")
        return ServerCredential(method=self.method, value=self.public_key or "", passphrase=self.passphrase)


class ServerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    host: str = Field(min_length=1, max_length=255)
    username: str = Field(min_length=1, max_length=255)
    port: int = Field(default=22, ge=1, le=65535)
    credential: CredentialInput | None = None


class ServerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    host: str | None = Field(default=None, min_length=1, max_length=255)
    username: str | None = Field(default=None, min_length=1, max_length=255)
    port: int | None = Field(default=None, ge=1, le=65535)
    credential: CredentialInput | None = None
    clear_credential: bool = False

    @model_validator(mode="after")
    def validate_conflicts(self) -> "ServerUpdate":
        if self.clear_credential and self.credential is not None:
            raise ValueError("cannot set and clear a credential at the same time")
        return self


class ServerRead(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: UUID
    name: str
    host: str
    username: str
    port: int
    access_method: AccessMethod
    has_credential: bool
    created_at: datetime
    updated_at: datetime


def server_read(server, has_credential: bool | None = None) -> ServerRead:
    return ServerRead(
        id=server.id,
        name=server.name,
        host=server.host,
        username=server.username,
        port=server.port,
        access_method=server.access_method,
        has_credential=server.credential_available if has_credential is None else has_credential,
        created_at=server.created_at,
        updated_at=server.updated_at,
    )