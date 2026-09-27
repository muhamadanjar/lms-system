import asyncio
from collections.abc import Awaitable, Callable

import asyncssh

from app.application.ports.ssh_bridge import (
    HostKeyChanged,
    InvalidCredentialFormat,
    SshAuthFailed,
    SshNetworkError,
    TermSize,
)
from app.domain.value_objects.content import AccessMethod


def _normalize_host_key(line) -> str:
    if isinstance(line, bytes):
        line = line.decode("utf-8", "replace")
    return " ".join((line if isinstance(line, str) else str(line)).split())


class _HostKeyClient(asyncssh.SSHClient):
    """TOFU host-key verification: accept unknown keys on first connect,
    reject any change afterwards."""

    def __init__(self, expected_host_key: str | None):
        if expected_host_key is not None:
            expected_host_key = _normalize_host_key(expected_host_key)
        self.expected_host_key: str | None = expected_host_key or None
        self.learned_host_key: str | None = None

    def validate_host_public_key(self, host: str, addr: str, port: int, key: asyncssh.SSHKey) -> bool:
        presented = _normalize_host_key(key.export_public_key())
        if self.expected_host_key is not None:
            if presented != self.expected_host_key:
                raise HostKeyChanged("ssh host key changed for server")
            return True
        self.learned_host_key = presented
        return True

    def validate_host_ca_key(self, host: str, addr: str, port: int, key: asyncssh.SSHKey) -> bool:
        return True


class _TerminalSession:
    """asyncssh SSHClientSession that pushes PTY output into an asyncio queue."""

    def __init__(self, queue: "asyncio.Queue[tuple[str, object]]"):
        self.queue: asyncio.Queue[tuple[str, object]] = queue
        self.channel = None

    def connection_made(self, channel) -> None:
        self.channel = channel
        self.queue.put_nowait(("made", None))

    def session_started(self) -> None:
        pass

    def data_received(self, data, datatype) -> None:
        self.queue.put_nowait(("data", data))

    def connection_lost(self, exc) -> None:
        self.queue.put_nowait(("lost", repr(exc) if exc else None))

    def eof_received(self) -> bool:
        self.queue.put_nowait(("lost", None))
        return True

    def exit_status_received(self, status) -> None:
        pass

    def exit_signal_received(self, sig, core, msg, lang) -> None:
        pass

    def xon_xoff_requested(self, client_echo, server_echo) -> None:
        pass


class AsyncSshSession:
    def __init__(self, connection, channel, queue: asyncio.Queue):
        self._connection = connection
        self._channel = channel
        self._queue = queue
        self._started = False
        self._closed = False

    async def _ensure_started(self) -> None:
        if self._started:
            return
        self._started = True
        while True:
            kind, _payload = await self._queue.get()
            if kind == "made":
                return
            if kind == "lost":
                raise SshNetworkError("ssh channel closed before the terminal was ready")

    async def send_input(self, data: str) -> None:
        if not self._closed:
            self._channel.write(data)

    async def resize(self, cols: int, rows: int) -> None:
        if not self._closed:
            try:
                self._channel.change_terminal_size(cols, rows)
            except Exception:
                pass

    async def next_output(self) -> str | None:
        while True:
            kind, payload = await self._queue.get()
            if kind == "made":
                continue
            if kind == "data":
                text = payload.decode("utf-8", "replace") if isinstance(payload, bytes) else str(payload)
                if text:
                    return text
                continue
            if kind == "lost":
                return None

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self._channel.close()
            await asyncio.wait_for(self._channel.wait_closed(), timeout=5)
        except Exception:
            pass
        try:
            self._connection.close()
            await asyncio.wait_for(self._connection.wait_closed(), timeout=5)
        except Exception:
            pass


class AsyncSshBridge:
    def __init__(self, connect_timeout: float = 15.0, auth_timeout: float = 15.0):
        self.connect_timeout = connect_timeout
        self.auth_timeout = auth_timeout

    async def _connect(self, owner_factory: Callable[[], _HostKeyClient], kwargs: dict) -> asyncssh.SSHClientConnection:
        try:
            return await asyncssh.connect(
                **kwargs,
                known_hosts=[],
                client_factory=owner_factory,
                connect_timeout=self.connect_timeout,
                login_timeout=self.auth_timeout,
            )
        except HostKeyChanged:
            raise
        except asyncssh.PermissionDenied as exc:
            raise SshAuthFailed("ssh authentication failed") from exc
        except asyncssh.DisconnectError as exc:
            raise SshAuthFailed(f"ssh authentication failed: {exc}") from exc
        except TimeoutError as exc:
            raise SshAuthFailed("ssh authentication timed out") from exc
        except (OSError, asyncssh.Error) as exc:
            raise SshNetworkError(f"cannot reach ssh host: {exc}") from exc

    async def open(
        self,
        *,
        host: str,
        port: int,
        username: str,
        method: AccessMethod,
        secret: str,
        passphrase: str | None,
        expected_host_key: str | None,
        term: TermSize,
    ) -> tuple[AsyncSshSession, str | None]:
        owner = None

        def _owner() -> _HostKeyClient:
            nonlocal owner
            owner = _HostKeyClient(expected_host_key)
            return owner

        kwargs: dict = {"host": host, "port": port, "username": username}
        if method is AccessMethod.PASSWORD:
            kwargs["password"] = secret
        else:
            try:
                import asyncssh  # already imported

                kwargs["client_keys"] = [asyncssh.import_private_key(secret, passphrase=passphrase or "")]
            except (ValueError, TypeError) as exc:
                raise InvalidCredentialFormat(f"invalid private key: {exc}") from exc

        connection = await self._connect(_owner, kwargs)

        queue: asyncio.Queue[tuple[str, object]] = asyncio.Queue()
        try:
            channel, _session = await connection.create_session(
                lambda: _TerminalSession(queue),
                request_pty=True,
                term_type="xterm-256color",
                term_size=(term.cols, term.rows),
            )
        except Exception as exc:
            connection.close()
            raise SshNetworkError(f"ssh terminal could not be created: {exc}") from exc

        session = AsyncSshSession(connection, channel, queue)
        try:
            await session._ensure_started()
        except Exception:
            await session.close()
            raise

        learned: str | None = None
        if expected_host_key is None and owner is not None:
            learned = owner.learned_host_key
        if learned is None and expected_host_key is None:
            try:
                host_key = connection.get_server_host_key()
                if host_key is not None:
                    learned = _normalize_host_key(host_key.export_public_key())
            except Exception:
                learned = None
        return session, learned