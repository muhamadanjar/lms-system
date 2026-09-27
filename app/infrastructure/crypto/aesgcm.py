import os
from base64 import b64decode
from uuid import UUID

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.application.ports.credential_cipher import CredentialEnvelope
from app.domain.exceptions import ValidationError


def encode_credential_key(raw: str) -> bytes:
    """Decode the base64 32-byte AES-GCM key supplied via SSH_CREDENTIAL_ENC_KEY."""
    try:
        key = b64decode(raw, validate=True)
    except Exception as exc:
        raise ValidationError("SSH_CREDENTIAL_ENC_KEY must be base64") from exc
    if len(key) != 32:
        raise ValidationError("SSH_CREDENTIAL_ENC_KEY must decode to 32 bytes")
    return key


class AesGcmCredentialCipher:
    """AES-256-GCM ciphertext-only credential codec.

    Secrets are never persisted or emitted; only (ciphertext, nonce, key_version)
    are stored. The server id and key version are bound as authenticated data.
    """

    def __init__(self, key: bytes, key_version: int = 1):
        if len(key) != 32:
            raise ValidationError("AES-GCM key must be 32 bytes")
        if key_version < 1:
            raise ValidationError("key_version must be a positive integer")
        self._cipher = AESGCM(key)
        self.key_version = key_version

    def encrypt(self, plaintext: str, server_id: UUID) -> CredentialEnvelope:
        nonce = os.urandom(12)
        ciphertext = self._cipher.encrypt(
            nonce,
            plaintext.encode("utf-8"),
            self._aad(server_id, self.key_version),
        )
        return CredentialEnvelope(ciphertext=ciphertext, nonce=nonce, key_version=self.key_version)

    def decrypt(self, envelope: CredentialEnvelope, server_id: UUID) -> str:
        aad = self._aad(server_id, envelope.key_version)
        try:
            plaintext = self._cipher.decrypt(envelope.nonce, envelope.ciphertext, aad)
        except InvalidTag as exc:
            raise ValidationError("cannot decrypt server credential") from exc
        return plaintext.decode("utf-8")

    @staticmethod
    def _aad(server_id: UUID, key_version: int) -> bytes:
        return f"{server_id}:{key_version}".encode("utf-8")