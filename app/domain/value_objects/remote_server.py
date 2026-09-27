from dataclasses import dataclass

from app.domain.exceptions import ValidationError
from app.domain.value_objects.content import AccessMethod


def ensure_host(value: str, field_name: str = "host") -> str:
    host = value.strip()
    if not host or len(host) > 255:
        raise ValidationError(f"{field_name} must contain 1-255 characters")
    if any(ch.isspace() for ch in host) or "/" in host:
        raise ValidationError(f"{field_name} must be a hostname or IP address")
    return host


def ensure_port(value: int) -> int:
    if not isinstance(value, int) or not (1 <= value <= 65535):
        raise ValidationError("port must be between 1 and 65535")
    return value


def ensure_ssh_secret(value: str, method: AccessMethod) -> str:
    secret = value.strip()
    if not secret:
        raise ValidationError("credential must not be empty")
    if len(secret) > 65536:
        raise ValidationError("credential exceeds 65536 characters")
    if method is AccessMethod.PASSWORD:
        if "PRIVATE KEY" in secret:
            raise ValidationError("password must not contain private key material")
        return secret
    if "-----BEGIN" in secret:
        if not secret.startswith("-----BEGIN OPENSSH PRIVATE KEY-----"):
            raise ValidationError("private key must be an OpenSSH private key block")
        return secret
    raise ValidationError("private key must be an OpenSSH private key PEM block")


@dataclass(frozen=True)
class ServerCredential:
    method: AccessMethod
    value: str
    passphrase: str | None = None

    def __post_init__(self) -> None:
        method = AccessMethod(self.method)
        value = ensure_ssh_secret(self.value, method)
        if method is AccessMethod.PASSWORD:
            if self.passphrase:
                raise ValidationError("passphrase is only allowed with PUBLIC_KEY method")
            passphrase: str | None = None
        else:
            if self.passphrase is not None and not self.passphrase.strip():
                raise ValidationError("passphrase must not be empty")
            passphrase = self.passphrase
        object.__setattr__(self, "method", method)
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "passphrase", passphrase)