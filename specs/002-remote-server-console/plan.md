# Implementation Plan: Remote Server Console

**Branch**: `002-remote-server-console` | **Date**: 2026-09-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-remote-server-console/spec.md`

## Summary

Add a Remote Server inventory aggregate and an interactive SSH console to `lms-system`.
Operators manage VPS endpoints through REST (`/api/v1/servers`) and open one live
terminal per server over WebSocket (`/api/v1/servers/{id}/console`). Credentials are
stored only as AES-GCM ciphertext (key from `SSH_CREDENTIAL_ENC_KEY`), decrypted
in-process during connection setup, and the console is bridged to the VPS via asyncssh
interactive PTY. A single-active-session registry enforces one console per server with
an explicit takeover flow. Auth reuses the existing User Management client and requires
the `servers.view` permission.

## Technical Context

**Language/Version**: Python 3.12.13 (repository runtime); code stays compatible with the
repository's existing syntax conventions.

**Primary Dependencies**: add `asyncssh` (SSH client bridge, asyncio-native) and
`cryptography` (AES-GCM credential cipher). Existing FastAPI 0.141.1, SQLModel 0.0.46,
Alembic 1.16.5, pytest/pytest-asyncio are reused. The `SecretResolver` port is **not**
used for console credentials — Remote Server uses ciphertext-only persistence instead.

**Storage**: PostgreSQL for production/integration behavior; SQLite for isolated unit and
migration smoke tests.

**Testing**: pytest + pytest-asyncio. unit/domain (entity invariants), unit/application
(use cases with fake cipher/bridge), integration/persistence (ciphertext-only,
raw-rejection), integration/ssh (against a disposable local OpenSSH server),
contract/http (REST + WS frames). No real VPS is touched in tests.

**Target Platform**: Linux-hosted FastAPI web service with PostgreSQL.

**Performance Goals**: Console latency from keystroke to remote echo must not add more
than ~15 ms per frame in baseline integration conditions (excluding network to VPS);
frame forwarding uses asyncio queues without polling loops.

**Constraints**:
- Domain stays framework-free (no FastAPI/SQLModel/asyncssh in `app/domain`).
- Raw password/private key never persist, log, or serialize (spec US4).
- Exactly one active console per Remote Server.
- WebSocket auth uses `Sec-WebSocket-Protocol`; token never logged.
- Changes to console/provisioning behavior require regression tests (standing rule).
- New code requires a real consumer; no placeholder architecture.

**Scale/Scope**: Inventory targets indexed, paginated access for up to 5,000 Remote
Servers. Monitoring/audit of console command history and command-restriction policies
are out of scope for this iteration.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] The feature has a real operator consumer: the Dashboard feature
      `services/dashboard/features/servers/`.
- [x] No secret material leaves the service boundary unencrypted.
- [x] Domain rules stay in `app/domain`; infra adapters implement ports.
- [ ] All four user stories have acceptance-scenario coverage in the plan phases.