from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.domain.value_objects.content import AccessMethod
from app.domain.value_objects.remote_server import ServerCredential


@dataclass(frozen=True)
class CredentialEnvelope:
    ciphertext: bytes
    nonce: bytes
    key_version: int


class CredentialCipher(Protocol):
    key_version: int

    def encrypt(self, credential: ServerCredential, server_id: UUID) -> CredentialEnvelope: ...

    def decrypt(
        self,
        envelope: CredentialEnvelope,
        server_id: UUID,
        method: AccessMethod,
    ) -> ServerCredential: ...
