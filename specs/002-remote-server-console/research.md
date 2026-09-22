# Research: Remote Server Console

## SSH client library: asyncssh vs paramiko

| Aspect | `asyncssh` (chosen) | `paramiko` |
| --- | --- | --- |
| Async-native | First-class asyncio API; clean fastapi/WS integration | Blocking; requires executor/thread to avoid stalling the event loop |
| Interactive PTY | `create_session(term_type=..., term_size=...)`, `set_windowsize` | `invoke_shell()` + ad-hoc resize; manual thread choreography |
| Host-key policy | `known_hosts` + `known_hosts_policy`, easy TOFU hook | Manual via `MissingHostKeyPolicy` |
| Dependency weight | Single package | Heavier dependency chain (cryptography, bcrypt, etc.) |
| Long-running channel tasks | Native coroutine style | Need `await loop.run_in_executor(...)` loops |

Decision: **asyncssh**. This service is asyncio-native (FastAPI, asyncpg, async
sessions); the console needs per-frame queued forwarding without blocking the event loop,
and PTY resize and TOFU host-key policy are first-class. A monitor watchdog task pairs
naturally with asyncssh's close futures.

## Credential cipher: AES-GCM via `cryptography`

- `cryptography` provides `AESGCM` (authenticated encryption, no padding, nonce 12
  bytes) — matches the ciphertext-only requirement.
- Openssl-based KDF (`scrypt`/`hkbdf`) derives the per-version key from
  `SSH_CREDENTIAL_ENC_KEY`; `credential_key_version` allows rotation without bulk re-encrypt.
- Rejected alternatives: Fernet (wrapper, ok but brings token/encoding semantics we do
  not need), NaCl/SecretBox (fine but adds another dependency), plain `pbkdf2` from
  stdlib (redundant given `cryptography`).

## Secret storage reconciliation (existing `SecretResolver`)

The repository already has a `SecretResolver` port (opaque `secret_ref` → value) used by
`LabEnvironmentSettings`. For console credentials we intentionally do **not** reuse it:
the Dashboard operator flow requires the credential to live with the Remote Server
aggregate and be usable immediately after provisioning, and there is no production
secrets-manager adapter in this service yet. The ciphertext-only model keeps the raw
secret out of persistence while avoiding a new infrastructure dependency (Vault/KMS).
The two modes may converge later behind the same `CredentialSource` abstraction if a
secrets manager is introduced.

## TOFU host-key policy

- First successful connect stores the OpenSSH host key line (or its SHA-256 fingerprint)
  on `remote_servers.host_key`.
- Later connects verify; mismatch → refuse session with a generic error (no key detail in
  logs, per US4).
- Comparison with storing nothing (skip verify): rejected — MITM exposure is unacceptable
  for admin consoles.
- Comparison with a global CA/known-hosts file: rejected for now — inventory is small and
  per-server TOFU matches the operator's mental model.

## Single-active-session enforcement

- In-process dict registry (server_id → session) is enough for one instance; no DB or
  distributed lock is needed at current scale. Document the single-instance assumption.
- Alternative (DB lease/lock) adds latency and complexity with no requirement today.

## Key rotation & migration

- `credential_key_version` on the row; decryption selects the key for that version.
- Env change of `SSH_CREDENTIAL_ENC_KEY` without bumping version invalidates existing
  rows → treated as intentional rotation following a data migration task; out of scope
  for the initial slice but the column exists.