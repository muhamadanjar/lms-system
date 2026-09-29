# Data Model: Remote Server Console

Management table owned by the `RemoteServer` aggregate. Lives in the same PostgreSQL
schema as the Learning Content tables; mapped with SQLModel under
`app/infrastructure/persistence/models/remote_server.py` and registered in the model
registry; Alembic migration `0003_remote_server`.

## `remote_servers`

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `id` | UUID (pk) | no | Default `uuid4`; stable identity |
| `name` | str(255) | no | Display name; unique |
| `host` | str(255) | no | IPv4/IPv6 or hostname |
| `port` | int | no | `1..65535`, default `22` |
| `username` | str(255) | no | SSH login user |
| `access_method` | varchar(11) | no | `PASSWORD` \| `PUBLIC_KEY` |
| `credential_ciphertext` | text | nullable | Base64 AES-GCM ciphertext blob |
| `credential_nonce` | text | nullable | Base64 AES-GCM nonce |
| `credential_key_version` | int | nullable | Key version in `SSH_CREDENTIAL_ENC_KEY` rotation |
| `host_key` | text | nullable | OpenSSH host key line captured at first connect (TOFU); first connect writes it, mismatch rejects |
| `created_at` | timestamptz | no | |
| `updated_at` | timestamptz | no | |
| `deleted_at` | timestamptz | nullable | Soft delete; consoles refused for deleted servers |

## Invariants (domain)

- `access_method` must match the credential shape:
  - `PASSWORD`: one password value, no key material.
  - `PUBLIC_KEY`: private key value (+ optional passphrase).
- Raw secret rejection: the credential value must not contain PEM armor markers
  (`BEGIN ... PRIVATE KEY`, `BEGIN RSA ...`) in any plaintext field, must be non-empty,
  and must be normalized before cipher (consistent with `lab_environment.py`).
- Only ciphertext + metadata persists; the plaintext credential exists only in memory
  for the lifetime of a decryption call and is wiped from local variables after connect.

## Credential envelope (stored bytes)

New credentials use a versioned plaintext representation inside the existing AES-GCM
envelope: a fixed `lms-remote-credential:v1:` marker followed by JSON containing the
credential value and optional passphrase. The wrapper is encrypted together with the
private key; no database migration or additional plaintext field is required. Existing
rows whose decrypted content lacks the marker remain supported as legacy values with
no passphrase.

```
credential_ciphertext = AESGCM(key).encrypt(nonce, plaintext, associated_data)
associated_data       = f"{server_id}:{credential_key_version}"
```

`key` is derived from `SSH_CREDENTIAL_ENC_KEY` (32-byte base64) plus `credential_key_version`
so rotation keeps old rows readable per-version.

## Console session registry (in-process, not persisted)

Keyed by `server_id → ConsoleSession` where `ConsoleSession` holds the active WebSocket,
the asyncssh channel, and `active_since`. Rebuilt on restart; any connectivity loss after
restart simply frees the slot. No command history or audit trail is stored.
