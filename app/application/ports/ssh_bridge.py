from dataclasses import dataclass
from typing import Protocol

from app.domain.value_objects.content import AccessMethod


@dataclass(frozen=True)
class TermSize:
    cols: int
    rows: int


class SshConsoleError(Exception):
    reason: str = "server_error"


class SshAuthFailed(SshConsoleError):
    reason = "ssh_auth_error"


class SshNetworkError(SshConsoleError):
    reason = "network_error"


class HostKeyChanged(SshConsoleError):
    "TOFU host key mismatch between stored and presented server host key."
    reason = "server_error"


class InvalidCredentialFormat(SshConsoleError):
    reason = "server_error"


class SshSession(Protocol):
    async def send_input(self, data: str) -> None: ...

    async def resize(self, cols: int, rows: int) -> None: ...

    async def next_output(self) -> str | None:
        "Return the next decoded terminal chunk, or None when the channel closed."

    async def close(self) -> None: ...


class SshBridge(Protocol):
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
    ) -> tuple[SshSession, str | None]:
        """
        Open an interactive PTY over SSH, applying TOFU host-key verification.
        Returns (session, learned_host_key) where learned_host_key is the
        normalized host key when the server had none stored.
        """
