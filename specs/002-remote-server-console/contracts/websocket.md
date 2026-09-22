# WebSocket Contract: Server Console

Endpoint: `WS /api/v1/servers/{server_id}/console`

## Handshake

- Authentication: dashboard session JWT sent in the `Sec-WebSocket-Protocol` request
  header (browsers cannot set arbitrary headers; subprotocol avoids token leakage into
  access/nginx logs from query strings).
- The server echoes the accepted subprotocol and replies with `ready` after the SSH
  channel is established.
- Required permission: `servers.view` (from `auth_info`). Rejected sockets are closed
  with WebSocket close reason `401` (unauthorized) or `403` (permission denied).
- Deleted (soft) server → close `404`.
- If the server is unreachable or auth fails, the socket closes with a structured reason;
  the reason string must never contain credential material.

## Single-active-session flow

1. On connect, the console registry is checked for `server_id`.
2. If already active → immediately send `conflict{active_since}` and do **not** create a
   PTY (socket stays open, waiting for the client's decision).
3. Client may (a) close the socket, or (b) send `takeover`.
4. On `takeover` → close the existing console with `closed{reason:"replaced"}`, free its
   SSH channel, then proceed to create a fresh PTY for this socket and send `ready`.

## Frames

All frames are JSON text. `data` payloads for `input`/`output` are UTF-8 strings
(shell interaction is textual). Binary frames are not used.

### Server → client

| frame | fields | notes |
| --- | --- | --- |
| `ready` | `{}` | SSH channel + PTY established |
| `output` | `{"data": "…"}` | PTY output chunk, streamed |
| `conflict` | `{"active_since": "RFC3339"}` | another console active; client split, awaiting decision |
| `closed` | `{"reason": "disconnected" \| "replaced" \| "server_deleted" \| "server_error" \| "auth_error" \| "network_error"}` | terminal state |
| `pong` | `{"id": 1}` | heartbeat reply |

### Client → server

| frame | fields | notes |
| --- | --- | --- |
| `input` | `{"data": "…"}` | keystroke/line bytes forwarded to PTY |
| `resize` | `{"cols": 120, "rows": 30}` | PTY window resize |
| `takeover` | `{}` | confirm takeover of the conflicting session |
| `ping` | `{"id": 1}` | heartbeat; timeout after N missed pongs closes session |

## Bridging (server-side)

- SSH client: `asyncssh.connect(host, port, username, client_keys/password, known_hosts=None)`.
- Host key policy: **TOFU** — on first successful connect the host key line is stored on
  the `remote_servers.host_key` column; on later connects a mismatch rejects the session
  (`closed{reason:"server_error"}` + generic message, no host key detail in logs).
- PTY: `await conn.create_session(term_type="xterm-256color", term_size=(rows, cols), ...)`.
- Frame forwarding uses asyncio queues: one reader task (PTY → `output` frames), one
  writer task (client frames → PTY stdin), so keystroke latency stays low.
- End-of-session: PTY exits or WebSocket closes → teardown both directions and remove
  registry entry.

## Heartbeat

Client sends `ping{id}`; server replies `pong{id}`. Server pings the client if idle;
after consecutive missed pongs or a dead socket, the console is closed and cleaned up.

## Test contract (see `tasks.md`)

Integration uses a disposable local OpenSSH server (container) for US2/US3; frame
sequences are asserted against the real WS endpoint. No real VPS required.