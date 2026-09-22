# Tasks: Remote Server Console

**Input**: Design documents from `/specs/002-remote-server-console/`
**Prerequisites**: `plan.md`, `spec.md`, `data-model.md`, `contracts/http.md`, `contracts/websocket.md`, `research.md`

## Execution Rules

- Every task is independently checkable and names the primary file or directory it changes.
- `[P]` indicates the task can run in parallel (no unfinished dependency on other tasks' files).
- User-story tasks are tagged `[US1]`..`[US4]`.
- Domain stays framework-free; FastAPI/SQLModel/asyncssh/cryptography stay under
  presentation/infrastructure.
- Complete foundational tasks before user-story implementation tasks.

## Phase 0: Research & Dependencies

- [ ] R001 Confirm asyncssh + cryptography versions compatible with Python 3.12 and the
      existing FastAPI/anyio stack; record findings in `research.md`.
- [ ] R002 Add `asyncssh` and `cryptography` to `requirements.txt` with pinned versions.

## Phase 1: Setup

- [ ] S001 Create test directories `tests/unit/domain/test_remote_server.py`,
      `tests/unit/application/`, `tests/integration/persistence/`,
      `tests/integration/ssh/`, `tests/contract/websocket/`.
- [ ] S002 Add reusable test fixtures in `tests/conftest.py`: fake `CredentialCipher`,
      fake `SshBridge`, and a disposable SSH server fixture (openssh container) for
      `tests/integration/ssh/`.

## Phase 2: Domain (framework-free)

- [ ] D001 Create `app/domain/entities/remote_server.py` — `RemoteServer` aggregate with
      `name`, `host`, `port`, `username`, `access_method`, credential value object,
      host key, soft-delete flags; invariant guards in `__post_init__`.
- [ ] D002 Create `app/domain/value_objects/remote_server.py` — `AccessMethod`
      (`PASSWORD`/`PUBLIC_KEY`) reusing `AccessMethod` from content if semantics match,
      `ServerCredential` (opaque value + passphrase) with raw-secret rejection
      (`BEGIN` markers / empty check) and normalization.
- [ ] D003 Create repository port `app/domain/repositories/remote_server.py` (list/detail/
      save/update/soft-delete by id, uniqueness on name) using `abc.ABC`/`Protocol`.
- [ ] D004 Create domain exceptions for `RemoteServerNotFound`, `DuplicateServerName`,
      `RawCredentialRejected`, `ConsoleConflict` in `app/domain/exceptions.py`.

## Phase 3: Application

- [ ] A001 Create ports in `app/application/ports/credential_cipher.py` (`encrypt`,
      `decrypt`, key-version aware) and `app/application/ports/ssh_bridge.py`
      (`open_pty`, `resize`, `close`, async iteration of output/incoming input).
- [ ] A002 Create `app/application/ports/console_registry.py` — protocol `ConsoleRegistry`
      with `acquire(server_id, session)`, `release(server_id)`, `active_since(server_id)`.
- [ ] A003 Create use cases `app/application/use_cases/server_inventory.py` —
      `CreateRemoteServer`, `ListRemoteServers`, `GetRemoteServer`, `UpdateRemoteServer`,
      `DeleteRemoteServer`. Secrets pass through the cipher; DTOs never include plaintext
      nor ciphertext (expose `has_credential`).
- [ ] A004 Create use case `app/application/use_cases/server_console.py` —
      `OpenConsole` (TOFU host-key capture, decrypt, acquire-or-conflict, takeover)
      and `CloseConsole`. Raw credential wiped from locals after connect.
- [ ] A005 [P] Unit tests for inventory use cases with fake cipher/repo (US1, US4).

## Phase 4: Infrastructure

- [ ] I001 Create `app/infrastructure/crypto/aesgcm.py` — `CredentialCipher` adapter
      (AES-GCM, 12-byte nonce, associated_data = server_id:key_version, key derivation
      from `SSH_CREDENTIAL_ENC_KEY` env + version).
- [ ] I002 Create `app/infrastructure/ssh/asyncssh_bridge.py` — `SshBridge` adapter:
      connect, `create_session(term_type="xterm-256color", term_size=...)`,
      `set_windowsize`, stdin/stdout asyncio queues, TOFU host-key persistence hook,
      graceful close.
- [ ] I003 Create `app/infrastructure/console/registry.py` — in-memory `ConsoleRegistry`
      (dict server_id → session, single instance assumption).
- [ ] I004 Create SQLModel model `app/infrastructure/persistence/models/remote_server.py`
      mapping `data-model.md`; register it in `app/infrastructure/persistence/
      model_registry.py`.
- [ ] I005 Create `app/infrastructure/persistence/repositories/remote_server_repository.py`
      implementing the repository port against SQLModel.
- [ ] I006 Add WebSocket/SSH settings to `app/config/config.py`: `SSH_CREDENTIAL_ENC_KEY`,
      console timeout, idle heartbeat interval.
- [ ] I007 Create Alembic migration `alembic/versions/0003_remote_server.py` (table +
      unique index on name, soft-delete filter default).

## Phase 5: Presentation

- [ ] P001 Create REST router `app/presentation/routers/servers.py` (per
      `contracts/http.md`) and Pydantic schemas in `app/presentation/schemas/server.py`
      with secret never in responses.
- [ ] P002 Create WS dependency in `app/presentation/dependencies/websocket.py` — reads
      `sec-websocket-protocol`, validates via `UserManagementAuthClient`, requires
      `servers.view`.
- [ ] P003 Create WS endpoint `app/presentation/websocket/console.py` implementing
      `contracts/websocket.md` (handshake, conflict, takeover, frames, heartbeat,
      teardown).
- [ ] P004 Wire routers + WS route + exception handlers in `app/main.py`; CORS origins
      include Dashboard origin.

## Phase 6: Tests & Validation

- [ ] T001 [P] Unit/domain tests: credential invariants, raw-secret rejection (US4).
- [ ] T002 [P] Integration/persistence tests: ciphertext-only persistence, PATCH without
      new secret keeps blob, soft-delete (US1, US4).
- [ ] T003 Integration/ssh tests: open console → PTY output, `echo`, resize, disconnect
      cleanup (US2).
- [ ] T004 Contract/websocket tests: conflict + takeover sequence (US3), closed reasons,
      auth rejection, heartbeat (pytest + websocket test client).
- [ ] T005 Contract/http tests: CRUD happy path + validation errors + permission
      responses, `has_credential` never plaintext (US1).
- [ ] T006 Migration smoke test: `0003_remote_server` upgrade/downgrade.
- [ ] T007 Run full `pytest`; confirm no secret string appears in any test log output.

## Checkpoint

Inventory CRUD works over REST with ciphertext-only persistence; an interactive console
opens over WebSocket against a disposable SSH server; conflict/takeover closes the old
console; no secret appears in responses, logs, or test output.