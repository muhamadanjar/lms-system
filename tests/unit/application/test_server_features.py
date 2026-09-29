import dataclasses

import pytest
from uuid import uuid4

from app.application.ports.ssh_bridge import TermSize
from app.application.ports.ssh_bridge import SshAuthFailed
from app.application.use_cases.server_console import (
    ConsoleAccepted,
    ConsoleConflict,
    ConsoleNotOpenable,
    ServerConsoleUseCase,
)
from app.application.use_cases.server_inventory import ServerInventoryUseCase
from app.domain.exceptions import ConflictError, NotFoundError, ValidationError
from app.domain.value_objects.content import AccessMethod
from app.domain.value_objects.remote_server import ServerCredential
from app.infrastructure.crypto.aesgcm import AesGcmCredentialCipher
from tests._fakes import FakeBridge, FakeRegistry, InMemoryServers

KEY = b"\x00" * 32


def make_cipher():
    return AesGcmCredentialCipher(KEY)


def make_tuple(uc):
    return uc


class FakeUnitOfWork:
    def __init__(self, store, uc):
        self.servers = store
        self.commits = 0
        self._uc = uc

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        pass


def inventory_uc(store, cipher):
    uow = FakeUnitOfWork(store, None)
    return ServerInventoryUseCase(lambda: uow), uow


def console_uc(store, cipher, bridge=None, registry=None):
    uow = FakeUnitOfWork(store, None)
    return ServerConsoleUseCase(
        lambda: uow,
        cipher,
        bridge or FakeBridge(),
        registry or FakeRegistry(),
    ), uow


def server(name="web01", host="10.0.0.5", username="admin", method=AccessMethod.PASSWORD, secret="pw"):
    from app.domain.entities.remote_server import RemoteServer

    return RemoteServer(name=name, host=host, username=username, access_method=method, credential=ServerCredential(method=method, value=secret))


@pytest.mark.unit
class TestServerInventory:
    async def test_create_encrypts_and_never_leaks(self):
        cipher = make_cipher()
        store = InMemoryServers(cipher)
        uc, uow = inventory_uc(store, cipher)
        created = await uc.create(
            name="web01",
            host="10.0.0.5",
            username="admin",
            access_method=AccessMethod.PASSWORD,
            credential=ServerCredential(method=AccessMethod.PASSWORD, value="hunter2"),
        )
        assert created.credential is None
        assert created.credential_available is True
        envelope = await store.get_credential_envelope(created.id)
        assert cipher.decrypt(envelope, created.id, AccessMethod.PASSWORD).value == "hunter2"
        assert uow.commits >= 1

    async def test_duplicate_name_conflicts(self):
        cipher = make_cipher()
        store = InMemoryServers(cipher)
        uc, _ = inventory_uc(store, cipher)
        await uc.create(name="web01", host="10.0.0.1", username="admin", access_method=AccessMethod.PASSWORD)
        with pytest.raises(ConflictError):
            await uc.create(name="web01", host="10.0.0.2", username="root", access_method=AccessMethod.PASSWORD)

    async def test_get_missing_raises_not_found(self):
        cipher = make_cipher()
        uc, _ = inventory_uc(InMemoryServers(cipher), cipher)
        with pytest.raises(NotFoundError):
            await uc.get(uuid4())

    async def test_update_keeps_existing_credential_when_not_supplied(self):
        cipher = make_cipher()
        store = InMemoryServers(cipher)
        uc, _ = inventory_uc(store, cipher)
        created = await uc.create(
            name="db01",
            host="10.0.0.6",
            username="admin",
            access_method=AccessMethod.PASSWORD,
            credential=ServerCredential(method=AccessMethod.PASSWORD, value="pw"),
        )
        updated = await uc.update(created.id, username="root", port=2222)
        assert updated.username == "root"
        assert updated.port == 2222
        assert updated.credential_available is True
        assert cipher.decrypt(await store.get_credential_envelope(created.id), created.id, AccessMethod.PASSWORD).value == "pw"

    async def test_update_clear_credential(self):
        cipher = make_cipher()
        store = InMemoryServers(cipher)
        uc, _ = inventory_uc(store, cipher)
        created = await uc.create(
            name="db02",
            host="10.0.0.6",
            username="admin",
            access_method=AccessMethod.PASSWORD,
            credential=ServerCredential(method=AccessMethod.PASSWORD, value="pw"),
        )
        updated = await uc.update(created.id, clear_credential=True)
        assert updated.credential_available is False
        assert await store.get_credential_envelope(created.id) is None

    async def test_clear_and_set_rejected(self):
        cipher = make_cipher()
        store = InMemoryServers(cipher)
        uc, _ = inventory_uc(store, cipher)
        created = await uc.create(name="c1", host="10.0.0.7", username="admin", access_method=AccessMethod.PASSWORD)
        with pytest.raises(ValidationError):
            await uc.update(
                created.id,
                clear_credential=True,
                credential=ServerCredential(method=AccessMethod.PASSWORD, value="pw"),
            )

    async def test_matched_credential_method_enforced(self):
        cipher = make_cipher()
        store = InMemoryServers(cipher)
        uc, _ = inventory_uc(store, cipher)
        created = await uc.create(name="c2", host="10.0.0.7", username="admin", access_method=AccessMethod.PASSWORD)
        with pytest.raises(ValidationError):
            await uc.update(
                created.id,
                credential=ServerCredential(method=AccessMethod.PUBLIC_KEY, value="ssh-ed25519 AAAAC"),
            )

    async def test_delete_soft_and_host_change_clears_host_key(self):
        cipher = make_cipher()
        store = InMemoryServers(cipher)
        uc, _ = inventory_uc(store, cipher)
        created = await uc.create(name="d1", host="10.0.0.8", username="admin", access_method=AccessMethod.PASSWORD)
        await store.update(dataclasses.replace(created, host_key="ssh-ed25519 known"))
        updated = await uc.update(created.id, host="10.0.0.99")
        assert updated.host_key is None
        await uc.delete(created.id)
        stored = await store.get_by_id(created.id)
        assert stored is not None and stored.deleted_at is not None


@pytest.mark.unit
class TestServerConsole:
    async def test_ssh_authentication_failure_has_specific_reason(self):
        cipher = make_cipher()
        store = InMemoryServers(cipher)
        bridge = FakeBridge()
        bridge.fail = SshAuthFailed("SSH authentication failed")
        uc, _ = console_uc(store, cipher, bridge=bridge)
        srv = await uc_inventory_create(store, cipher)

        with pytest.raises(ConsoleNotOpenable) as exc:
            await uc.open(srv.id, TermSize(80, 24))

        assert exc.value.reason == "ssh_auth_error"

    async def test_open_passes_decrypted_key_passphrase_to_ssh_bridge(self):
        cipher = make_cipher()
        store = InMemoryServers(cipher)
        bridge = FakeBridge()
        inventory, _ = inventory_uc(store, cipher)
        key = "-----BEGIN OPENSSH PRIVATE KEY-----\nZmFrZS1rZXk=\n-----END OPENSSH PRIVATE KEY-----"
        saved = await inventory.create(
            name="keybox",
            host="10.0.0.11",
            username="deploy",
            access_method=AccessMethod.PUBLIC_KEY,
            credential=ServerCredential(
                method=AccessMethod.PUBLIC_KEY,
                value=key,
                passphrase="private-key-passphrase",
            ),
        )
        uc, _ = console_uc(store, cipher, bridge=bridge)

        await uc.open(saved.id, TermSize(80, 24))

        assert bridge.calls[0]["secret"] == key
        assert bridge.calls[0]["passphrase"] == "private-key-passphrase"

    async def test_open_missing_credential_not_openable(self):
        cipher = make_cipher()
        store = InMemoryServers(cipher)
        uc, _ = console_uc(store, cipher)
        from app.domain.entities.remote_server import RemoteServer

        plain = RemoteServer(name="x", host="10.0.0.9", username="u", access_method=AccessMethod.PASSWORD)
        blocked = await store.create(plain)
        with pytest.raises(ConsoleNotOpenable) as exc:
            await uc.open(blocked.id, TermSize(80, 24))
        assert exc.value.reason == "server_error"

    async def test_single_active_session_and_takeover(self):
        cipher = make_cipher()
        store = InMemoryServers(cipher)
        uc, _ = console_uc(store, cipher)
        srv = await uc_inventory_create(store, cipher)
        first = await uc.open(srv.id, TermSize(80, 24), session_id="s1")
        assert isinstance(first, ConsoleAccepted)
        second = await uc.open(srv.id, TermSize(80, 24), session_id="s2")
        assert isinstance(second, ConsoleConflict)
        taken = await uc.takeover(srv.id, TermSize(80, 24), session_id="s3")
        assert isinstance(taken, ConsoleAccepted)
        assert taken.session_id == "s3"

    async def test_takeover_closes_previous_session(self):
        cipher = make_cipher()
        store = InMemoryServers(cipher)
        uc, _ = console_uc(store, cipher)
        srv = await uc_inventory_create(store, cipher)
        first = await uc.open(srv.id, TermSize(80, 24), session_id="s1")
        await uc.takeover(srv.id, TermSize(80, 24), session_id="s2")
        assert first.session.closed is True

    async def test_host_key_persisted(self):
        cipher = make_cipher()
        store = InMemoryServers(cipher)
        uc, _ = console_uc(store, cipher)
        srv = await uc_inventory_create(store, cipher)
        await uc.open(srv.id, TermSize(80, 24), session_id="s1")
        persisted = await store.get_by_id(srv.id)
        assert persisted is not None
        assert persisted.host_key == "ssh-ed25519 fake"

    async def test_console_sends_input_and_resize(self):
        cipher = make_cipher()
        store = InMemoryServers(cipher)
        uc, _ = console_uc(store, cipher)
        srv = await uc_inventory_create(store, cipher)
        accepted = await uc.open(srv.id, TermSize(80, 24), session_id="s1")
        await accepted.session.send_input("ls -la\n")
        await accepted.session.resize(100, 40)
        assert await accepted.session.next_output() == "<echo>ls -la\n"
        assert accepted.session.term_sizes == [(100, 40)]


async def uc_inventory_create(store, cipher):
    uc, _ = inventory_uc(store, cipher)
    created = await uc.create(
        name="web01",
        host="10.0.0.5",
        username="admin",
        access_method=AccessMethod.PASSWORD,
        credential=ServerCredential(method=AccessMethod.PASSWORD, value="pw"),
    )
    return created
