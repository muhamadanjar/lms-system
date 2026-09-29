import os

import pytest

from app.domain.entities.remote_server import RemoteServer
from app.domain.exceptions import NotFoundError
from app.domain.value_objects.content import AccessMethod
from app.domain.value_objects.remote_server import ServerCredential
from app.infrastructure.crypto.aesgcm import AesGcmCredentialCipher
from app.infrastructure.persistence.models.remote_server import RemoteServer as RemoteServerRow
from app.infrastructure.persistence.repositories.remote_server_repository import (
    SqlModelRemoteServerRepository,
)


def make_server(
    name: str = "web-01",
    host: str = "10.0.0.1",
    mode: AccessMethod = AccessMethod.PASSWORD,
    credential: str | None = "hunter2",
    include_clear: bool = False,
    passphrase: str | None = None,
) -> RemoteServer:
    server = RemoteServer(
        name=name,
        host=host,
        port=22,
        username="root",
        access_method=mode,
        credential=ServerCredential(method=mode, value=credential, passphrase=passphrase) if credential is not None else None,
    )
    if include_clear:
        server._clear_credential = True  # type: ignore[attr-defined]
    return server


async def test_create_encrypts_credential_and_mapping_never_leaks(session):
    cipher = AesGcmCredentialCipher(os.urandom(32))
    repo = SqlModelRemoteServerRepository(session, cipher)
    server = make_server()
    created = await repo.create(server)
    await session.commit()

    assert created.credential is None
    assert created.credential_available is True

    row = await session.get(RemoteServerRow, created.id)
    assert row.credential_ciphertext is not None
    assert row.credential_ciphertext != "hunter2"
    assert "hunter2" not in row.credential_ciphertext

    envelope = await repo.get_credential_envelope(created.id)
    decrypted = cipher.decrypt(envelope, created.id, AccessMethod.PASSWORD)
    assert decrypted.value == "hunter2"
    assert decrypted.passphrase is None


async def test_get_credential_envelope_returns_none_for_clear_server(session):
    cipher = AesGcmCredentialCipher(os.urandom(32))
    repo = SqlModelRemoteServerRepository(session, cipher)
    server = make_server(credential=None)
    created = await repo.create(server)
    await session.commit()

    assert created.credential_available is False
    assert await repo.get_credential_envelope(created.id) is None


async def test_reload_with_same_cipher_can_decrypt(session):
    cipher = AesGcmCredentialCipher(os.urandom(32))
    repo = SqlModelRemoteServerRepository(session, cipher)
    created = await repo.create(make_server())
    await session.commit()

    loaded = await repo.get_by_id(created.id)
    assert loaded is not None
    assert loaded.credential is None
    assert loaded.credential_available is True
    envelope = await repo.get_credential_envelope(created.id)
    assert cipher.decrypt(envelope, created.id, AccessMethod.PASSWORD).value == "hunter2"


async def test_update_without_credential_preserves_secret(session):
    cipher = AesGcmCredentialCipher(os.urandom(32))
    repo = SqlModelRemoteServerRepository(session, cipher)
    created = await repo.create(make_server())
    await session.commit()

    changed = RemoteServer(
        id=created.id,
        name="web-01",
        host="10.0.0.2",
        port=22,
        username="deploy",
        access_method=AccessMethod.PASSWORD,
        created_at=created.created_at,
    )
    updated = await repo.update(changed)
    await session.commit()

    assert updated.host == "10.0.0.2"
    envelope = await repo.get_credential_envelope(created.id)
    assert cipher.decrypt(envelope, created.id, AccessMethod.PASSWORD).value == "hunter2"


async def test_update_can_clear_or_replace_credential(session):
    cipher = AesGcmCredentialCipher(os.urandom(32))
    repo = SqlModelRemoteServerRepository(session, cipher)
    created = await repo.create(make_server())
    await session.commit()

    clear = RemoteServer(
        id=created.id,
        name="web-01",
        host="10.0.0.1",
        port=22,
        username="root",
        access_method=AccessMethod.PASSWORD,
        created_at=created.created_at,
    )
    clear._clear_credential = True  # type: ignore[attr-defined]
    await repo.update(clear)
    await session.commit()
    assert await repo.get_credential_envelope(created.id) is None
    assert (await repo.get_by_id(created.id)).credential_available is False

    replace = RemoteServer(
        id=created.id,
        name="web-01",
        host="10.0.0.1",
        port=22,
        username="root",
        access_method=AccessMethod.PASSWORD,
        credential=ServerCredential(method=AccessMethod.PASSWORD, value="new-secret"),
        created_at=created.created_at,
    )
    await repo.update(replace)
    await session.commit()
    envelope = await repo.get_credential_envelope(created.id)
    assert cipher.decrypt(envelope, created.id, AccessMethod.PASSWORD).value == "new-secret"


async def test_soft_delete_hides_from_list_and_is_idempotent(session):
    repo = SqlModelRemoteServerRepository(session, AesGcmCredentialCipher(os.urandom(32)))
    created = await repo.create(make_server())
    await session.commit()

    assert await repo.soft_delete(created.id) is True
    await session.commit()
    assert await repo.soft_delete(created.id) is False

    assert (await repo.get_by_id(created.id)) is not None
    assert await repo.list() == []
    assert await repo.count() == 0
    assert len(await repo.list(include_deleted=True)) == 1
    assert await repo.count(include_deleted=True) == 1


async def test_search_and_pagination(session):
    repo = SqlModelRemoteServerRepository(session, AesGcmCredentialCipher(os.urandom(32)))
    for index in range(5):
        await repo.create(make_server(name=f"web-{index:02d}", host=f"10.0.0.{index + 1}"))
    await session.commit()

    assert len(await repo.list(limit=2)) == 2
    assert len(await repo.list(offset=2, limit=10)) == 3
    assert await repo.count() == 5

    matched = await repo.list(search="web-02")
    assert [s.name for s in matched] == ["web-02"]

    by_host = await repo.list(search="10.0.0.4")
    assert [s.name for s in by_host] == ["web-03"]


async def test_update_missing_server_raises(session):
    repo = SqlModelRemoteServerRepository(session, AesGcmCredentialCipher(os.urandom(32)))
    ghost = make_server()
    with pytest.raises(NotFoundError):
        await repo.update(ghost)


async def test_public_key_credential_round_trip(session):
    cipher = AesGcmCredentialCipher(os.urandom(32))
    repo = SqlModelRemoteServerRepository(session, cipher)
    pubkey = "-----BEGIN OPENSSH PRIVATE KEY-----\nZmFrZS1rZXk=\n-----END OPENSSH PRIVATE KEY-----"
    server = make_server(
        mode=AccessMethod.PUBLIC_KEY,
        credential=pubkey,
        name="keybox",
        passphrase="private-key-passphrase",
    )
    created = await repo.create(server)
    await session.commit()

    envelope = await repo.get_credential_envelope(created.id)
    decrypted = cipher.decrypt(envelope, created.id, AccessMethod.PUBLIC_KEY)
    assert decrypted.value == pubkey
    assert decrypted.passphrase == "private-key-passphrase"
    row = await session.get(RemoteServerRow, created.id)
    assert row is not None
    assert "private-key-passphrase" not in row.credential_ciphertext


async def test_decrypt_legacy_unwrapped_credential(session):
    from app.application.ports.credential_cipher import CredentialEnvelope

    key = os.urandom(32)
    cipher = AesGcmCredentialCipher(key)
    repo = SqlModelRemoteServerRepository(session, cipher)
    created = await repo.create(make_server())
    await session.commit()

    nonce = os.urandom(12)
    ciphertext = cipher._cipher.encrypt(
        nonce,
        b"legacy-private-key",
        cipher._aad(created.id, cipher.key_version),
    )
    legacy = CredentialEnvelope(ciphertext=ciphertext, nonce=nonce, key_version=cipher.key_version)
    decrypted = cipher.decrypt(legacy, created.id, AccessMethod.PASSWORD)
    assert decrypted.value == "legacy-private-key"
    assert decrypted.passphrase is None
