import asyncio

import asyncssh
import pytest

from app.application.ports.ssh_bridge import HostKeyChanged, SshAuthFailed, TermSize
from app.domain.value_objects.content import AccessMethod
from app.infrastructure.ssh.asyncssh_bridge import AsyncSshBridge


class EchoSession(asyncssh.SSHServerSession):
    def __init__(self):
        self._channel = None

    def connection_made(self, channel):
        self._channel = channel

    def session_started(self) -> None:
        pass

    def shell_requested(self) -> bool:
        return True

    def pty_requested(self, term_type: str, term_size: tuple[int, ...],
                      term_modes: dict) -> bool:
        return True

    def data_received(self, data, datatype) -> None:
        if self._channel is not None:
            self._channel.write("ECHO:" + data)

    def eof_received(self) -> bool:
        return False

    def connection_lost(self, exc) -> None:
        pass


class TestSSHServer(asyncssh.SSHServer):
    USER = "admin"
    PASSWORD = "hunter2"

    def begin_auth(self, username: str) -> bool:
        if username != self.USER:
            return False
        return True

    def password_auth_supported(self) -> bool:
        return True

    async def validate_password(self, username: str, password: str) -> bool:
        return username == self.USER and password == self.PASSWORD

    def session_requested(self):
        return EchoSession()


@pytest.mark.integration
class TestAsyncSshBridge:
    @pytest.fixture
    async def bridge_server(self):
        key = asyncssh.generate_private_key("ssh-ed25519")
        server = await asyncssh.create_server(
            lambda: TestSSHServer(),
            host="127.0.0.1",
            port=0,
            server_host_keys=[key],
        )
        port = server.sockets[0].getsockname()[1]
        yield ("127.0.0.1", port)
        server.close()
        await server.wait_closed()

    @pytest.mark.asyncio
    async def test_password_auth_and_persist_host_key(self, bridge_server):
        host, port = bridge_server
        bridge = AsyncSshBridge(connect_timeout=10, auth_timeout=20)
        session, learned = await bridge.open(
            host=host,
            port=port,
            username=TestSSHServer.USER,
            method=AccessMethod.PASSWORD,
            secret=TestSSHServer.PASSWORD,
            passphrase=None,
            expected_host_key=None,
            term=TermSize(cols=100, rows=30),
        )
        assert learned is not None and learned.startswith("ssh-ed25519")
        assert session is not None

        await session.send_input("ping\n")
        chunk = await session.next_output()
        assert chunk is not None and "ECHO:ping" in chunk

        await session.resize(120, 40)
        await session.close()

    @pytest.mark.asyncio
    async def test_reconnect_with_stored_host_key_verifies(self, bridge_server):
        host, port = bridge_server
        bridge = AsyncSshBridge(connect_timeout=10, auth_timeout=20)
        session, learned = await bridge.open(
            host=host,
            port=port,
            username=TestSSHServer.USER,
            method=AccessMethod.PASSWORD,
            secret=TestSSHServer.PASSWORD,
            passphrase=None,
            expected_host_key=None,
            term=TermSize(cols=100, rows=30),
        )
        await session.close()
        reconnected, _ = await bridge.open(
            host=host,
            port=port,
            username=TestSSHServer.USER,
            method=AccessMethod.PASSWORD,
            secret=TestSSHServer.PASSWORD,
            passphrase=None,
            expected_host_key=learned,
            term=TermSize(cols=100, rows=30),
        )
        await reconnected.close()

    @pytest.mark.asyncio
    async def test_changed_host_key_rejected(self, bridge_server):
        host, port = bridge_server
        bridge = AsyncSshBridge(connect_timeout=10, auth_timeout=20)
        session, _ = await bridge.open(
            host=host,
            port=port,
            username=TestSSHServer.USER,
            method=AccessMethod.PASSWORD,
            secret=TestSSHServer.PASSWORD,
            passphrase=None,
            expected_host_key=None,
            term=TermSize(cols=100, rows=30),
        )
        await session.close()
        other = asyncssh.generate_private_key("ssh-ed25519").export_public_key()
        with pytest.raises(HostKeyChanged):
            await bridge.open(
                host=host,
                port=port,
                username=TestSSHServer.USER,
                method=AccessMethod.PASSWORD,
                secret=TestSSHServer.PASSWORD,
                passphrase=None,
                expected_host_key=other,
                term=TermSize(cols=100, rows=30),
            )

    @pytest.mark.asyncio
    async def test_bad_password_rejected(self, bridge_server):
        host, port = bridge_server
        bridge = AsyncSshBridge(connect_timeout=10, auth_timeout=20)
        with pytest.raises(SshAuthFailed):
            await bridge.open(
                host=host,
                port=port,
                username=TestSSHServer.USER,
                method=AccessMethod.PASSWORD,
                secret="wrong",
                passphrase=None,
                expected_host_key=None,
                term=TermSize(cols=100, rows=30),
            )