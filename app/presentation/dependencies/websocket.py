from fastapi import WebSocket

from app.application.ports.auth import CurrentUser
from app.config.config import get_settings
from app.infrastructure.auth.usermanagement_client import (
    AuthServiceRejected,
    AuthServiceUnavailable,
    UserManagementAuthClient,
)

AUTH_SUBPROTOCOL_PREFIX = "bearer."


class WebSocketAuthError(Exception):
    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


def _subprotocols(ws: WebSocket) -> list[str]:
    raw = ws.headers.get("sec-websocket-protocol")
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def extract_bearer_subprotocol(ws: WebSocket) -> tuple[str, str]:
    """Find `bearer.<token>`. Returns (token, exact_protocol) to echo."""
    for protocol in _subprotocols(ws):
        lower = protocol.lower()
        if lower.startswith(AUTH_SUBPROTOCOL_PREFIX):
            token = protocol[len(AUTH_SUBPROTOCOL_PREFIX):].strip()
            if token:
                return token, protocol
    raise WebSocketAuthError("missing bearer token in Sec-WebSocket-Protocol")


async def authenticate_websocket(ws: WebSocket) -> tuple[CurrentUser, str]:
    """Validate JWT supplied via the Sec-WebSocket-Protocol header.

    Must be called BEFORE ws.accept(); returns (user, subprotocol_to_echo).
    """
    try:
        token, echo = extract_bearer_subprotocol(ws)
    except WebSocketAuthError:
        raise

    client = UserManagementAuthClient(get_settings().usermanagement)
    try:
        user = await client.get_current_user(f"Bearer {token}")
    except AuthServiceRejected as exc:
        raise WebSocketAuthError("invalid authentication token") from exc
    except AuthServiceUnavailable as exc:
        raise WebSocketAuthError("authentication service unavailable") from exc
    return user, echo