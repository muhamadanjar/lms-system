from dataclasses import dataclass, field
from datetime import datetime

from app.domain.entities.base import BaseEntity
from app.domain.exceptions import ValidationError
from app.domain.value_objects.content import AccessMethod
from app.domain.value_objects.remote_server import (
    ServerCredential,
    ensure_host,
    ensure_port,
)


@dataclass
class RemoteServer(BaseEntity):
    name: str = ""
    host: str = ""
    username: str = ""
    port: int = 22
    access_method: AccessMethod = AccessMethod.PASSWORD
    credential: ServerCredential | None = None
    credential_available: bool = False
    host_key: str | None = None
    deleted_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValidationError("name is required")
        self.name = self.name.strip()
        self.host = ensure_host(self.host)
        self.port = ensure_port(self.port)
        if not self.username or not self.username.strip():
            raise ValidationError("username is required")
        self.username = self.username.strip()
        self.access_method = AccessMethod(self.access_method)
        if self.credential is not None:
            if self.credential.method is not self.access_method:
                raise ValidationError("credential method must match access method")
            self.credential_available = True
        if self.created_at.tzinfo is None or self.updated_at.tzinfo is None:
            raise ValidationError("created_at and updated_at must be timezone-aware")
        if self.updated_at < self.created_at:
            raise ValidationError("updated_at cannot precede created_at")
        if self.deleted_at is not None and self.deleted_at.tzinfo is None:
            raise ValidationError("deleted_at must be timezone-aware")