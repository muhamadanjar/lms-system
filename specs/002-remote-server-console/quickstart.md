# Quickstart: Remote Server Console

This guide validates the implemented console slice. The console talks to a real SSH
endpoint only in integration tests, which spin up a disposable local OpenSSH server;
no real VPS is required.

## Prerequisites

- Python 3.12 environment with project dependencies installed (incl. `asyncssh`,
  `cryptography`).
- PostgreSQL available for integration tests (`DATABASE__URL`).
- `SSH_CREDENTIAL_ENC_KEY` set to a 32-byte base64 value for credential encryption
  (defaults are forbidden for production; tests inject their own key).
- CORS settings allow the Dashboard origin for the WebSocket handshake.

## Environment

```bash
SSH_CREDENTIAL_ENC_KEY=...  # 32-byte base64
CORS__ALLOWED_ORIGINS=http://localhost:3000   # dashboard
```

## Schema Validation

From the repository root:

```bash
alembic upgrade head
alembic check
alembic downgrade -1
alembic upgrade head
```

Expected: `remote_servers` table exists after upgrade; `alembic check` clean; downgrade
removes the table; upgrade recreates it.

## REST smoke test

```bash
# requires servers.create + servers.view
curl -X POST http://localhost:8000/api/v1/servers \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"name":"demo","host":"127.0.0.1","port":22,"username":"test","access_method":"PASSWORD","credential":{"value":"secret"}}'

curl http://localhost:8000/api/v1/servers \
  -H "Authorization: Bearer $JWT"
```

Expected: create returns `has_credential: true`; list/detail responses contain no
credential field.

## Automated Tests

```bash
pytest -q tests/unit/domain tests/unit/application
pytest -q tests/integration/persistence
pytest -q tests/integration/ssh
pytest -q tests/contract/http tests/contract/websocket
pytest -q tests/integration/migrations
```

Verification that no secret leaks: run the suite with a sentinel secret and grep test
output for it (T007).