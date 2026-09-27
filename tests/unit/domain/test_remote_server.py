import pytest

from app.domain.entities.remote_server import RemoteServer
from app.domain.exceptions import ValidationError
from app.domain.value_objects.content import AccessMethod
from app.domain.value_objects.remote_server import (
    ServerCredential,
    ensure_host,
    ensure_port,
    ensure_ssh_secret,
)


class TestServerCredential:
    def test_password_credential(self):
        credential = ServerCredential(method=AccessMethod.PASSWORD, value="  hunter2  ")
        assert credential.value == "hunter2"
        assert credential.passphrase is None

    def test_public_key_credential(self):
        credential = ServerCredential(
            method=AccessMethod.PUBLIC_KEY,
            value="-----BEGIN OPENSSH PRIVATE KEY-----\n"
            "MIIEowIBAAKCAQEAwL2uP6xJ6sQ0VwmDlKpXrFw5C\n"
            "-----END OPENSSH PRIVATE KEY-----\n",
            passphrase="secret",
        )
        assert credential.method is AccessMethod.PUBLIC_KEY
        assert credential.passphrase == "secret"

    def test_password_rejects_private_key_material(self):
        with pytest.raises(ValidationError):
            ServerCredential(method=AccessMethod.PASSWORD, value="-----BEGIN PRIVATE KEY-----")

    def test_public_key_accepts_private_key_pem(self):
        credential = ServerCredential(
            method=AccessMethod.PUBLIC_KEY,
            value="-----BEGIN OPENSSH PRIVATE KEY-----\n"
            "MIIEowIBAAKCAQEAwL2uP6xJ6sQ0VwmDlKpXrFw5C\n"
            "-----END OPENSSH PRIVATE KEY-----\n",
            passphrase="secret",
        )
        assert credential.method is AccessMethod.PUBLIC_KEY
        assert credential.passphrase == "secret"

    def test_public_key_rejects_bogus_line(self):
        with pytest.raises(ValidationError):
            ServerCredential(method=AccessMethod.PUBLIC_KEY, value="not-a-key")

    def test_password_rejects_passphrase(self):
        with pytest.raises(ValidationError):
            ServerCredential(method=AccessMethod.PASSWORD, value="pw", passphrase="pp")

    def test_public_key_rejects_empty(self):
        with pytest.raises(ValidationError):
            ServerCredential(method=AccessMethod.PUBLIC_KEY, value="   ")


class TestRemoteServerEntity:
    def test_minimal_entity(self):
        server = RemoteServer(name="web01", host="10.0.0.5", username="admin")
        assert server.port == 22
        assert server.access_method is AccessMethod.PASSWORD
        assert server.credential_available is False

    def test_credential_sets_available(self):
        server = RemoteServer(
            name="web01",
            host="10.0.0.5",
            username="admin",
            credential=ServerCredential(method=AccessMethod.PASSWORD, value="pw"),
        )
        assert server.credential_available is True

    def test_rejects_blank_name(self):
        with pytest.raises(ValidationError):
            RemoteServer(name="  ", host="10.0.0.5", username="admin")

    def test_rejects_bad_host(self):
        with pytest.raises(ValidationError):
            RemoteServer(name="web01", host="http://10.0.0.5/x", username="admin")

    def test_rejects_bad_port(self):
        with pytest.raises(ValidationError):
            RemoteServer(name="web01", host="10.0.0.5", username="admin", port=0)

    def test_rejects_mismatched_credential_method(self):
        with pytest.raises(ValidationError):
            RemoteServer(
                name="web01",
                host="10.0.0.5",
                username="admin",
                access_method=AccessMethod.PUBLIC_KEY,
                credential=ServerCredential(method=AccessMethod.PASSWORD, value="pw"),
            )


class TestHelpers:
    def test_ensure_host_strips(self):
        assert ensure_host(" 10.0.0.5 ") == "10.0.0.5"

    def test_ensure_host_rejects_space(self):
        with pytest.raises(ValidationError):
            ensure_host("10.0.0.5 evil")

    def test_ensure_port_bounds(self):
        assert ensure_port(1) == 1
        assert ensure_port(65535) == 65535
        with pytest.raises(ValidationError):
            ensure_port(65536)
        with pytest.raises(ValidationError):
            ensure_port("22")

    def test_ensure_ssh_secret_password_allows_emoji_tokens(self):
        assert ensure_ssh_secret("p@ss w0rd!", AccessMethod.PASSWORD) == "p@ss w0rd!"