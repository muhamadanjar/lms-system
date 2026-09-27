from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class CredentialEnvelope:
    ciphertext: bytes
    nonce: bytes
    key_version: int


class CredentialCipher(Protocol):
    key_version: int

    def encrypt(self, plaintext: str, server_id: UUID) -> CredentialEnvelope: ...

    def decrypt(self, envelope: CredentialEnvelope, server_id: UUID) -> str: ...