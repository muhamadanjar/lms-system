from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID

from app.domain.entities.base import ContentEntity
from app.domain.exceptions import ValidationError
from app.domain.value_objects.content import AccessMethod, ensure_text


@dataclass
class LabEnvironmentSettings(ContentEntity):
    section_id: UUID = field(default=None)  # type: ignore[assignment]
    provider: str = ""
    region: Optional[str] = None
    image: str = ""
    cpu: int = 1
    memory_mb: int = 1024
    storage_gb: int = 10
    access_method: AccessMethod = AccessMethod.PASSWORD
    username: str = ""
    password_secret_ref: Optional[str] = None
    public_key: Optional[str] = None
    private_key_secret_ref: Optional[str] = None
    network_policy: Optional[str] = None
    timeout_seconds: int = 3600
    cleanup_policy: str = "DELETE_ON_FINISH"

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.section_id is None:
            raise ValidationError("section_id is required")
        self.provider = ensure_text(self.provider, "provider", 100)
        self.image = ensure_text(self.image, "image", 255)
        self.username = ensure_text(self.username, "username", 255)
        self.access_method = AccessMethod(self.access_method)
        if self.cpu <= 0 or self.memory_mb <= 0 or self.storage_gb <= 0 or self.timeout_seconds <= 0:
            raise ValidationError("lab resources and timeout must be positive")
        if self.access_method is AccessMethod.PASSWORD:
            if not self.password_secret_ref or self.private_key_secret_ref or self.public_key:
                raise ValidationError("PASSWORD access requires only password_secret_ref")
        if self.access_method is AccessMethod.PUBLIC_KEY:
            if not self.private_key_secret_ref or not self.public_key or self.password_secret_ref:
                raise ValidationError("PUBLIC_KEY access requires public and private key references")
        for raw in (self.password_secret_ref, self.private_key_secret_ref):
            if raw and "BEGIN " in raw:
                raise ValidationError("raw secrets are not accepted; use an opaque reference")
