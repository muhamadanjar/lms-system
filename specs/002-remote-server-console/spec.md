# Feature Specification: Remote Server Console

**Feature Branch**: `002-remote-server-console`

**Created**: 2026-09-23

**Status**: Draft

**Input**: Dashboard requirement — a VPS server inventory plus a full web terminal
(SSH) so operators can manage VPS servers through the platform, with the backend
handled here (in `lms-system`) over a FastAPI WebSocket. Each action from the browser
terminal goes through this service; the terminal behaves like an interactive SSH
session opened from a shell.

Related dashboard docs: `services/dashboard/docs/plans/servers-vps-terminal.md`,
`services/dashboard/docs/features/servers-vps-console.md`.

## Clarifications

### Session 2026-09-23

- Q: Apakah Remote Server memakai aggregate Lab environment yang sudah ada? → A: Tidak.
  `RemoteServer` adalah aggregate baru untuk operator console, terpisah dari
  `LabEnvironmentSettings` (yang terikat `section_id` dan memakai secret reference
  untuk lab belajar). Keduanya berbagi aturan keamanan rahasia yang sama.
- Q: Bagaimana kredensial SSH (password / private key) disimpan? → A: Ciphertext-only.
  Hanya AES-GCM ciphertext + nonce + key version yang dipersist; plaintext password /
  private key tidak pernah masuk database, log, error response, atau fixture. Key
  di-env `SSH_CREDENTIAL_ENC_KEY` (32-byte base64). Invariant domain menolak raw secret.
- Q: Berapa sesi terminal yang boleh aktif untuk satu Remote Server? → A: Tepat satu.
  Koneksi kedua menerima frame `conflict`; dia boleh "take over" setelah konfirmasi
  pengguna, yang menutup sesi lama dan menggantinya.
- Q: Bagaimana browser mengotentikasi WebSocket? → A: JWT akses dashboard dikirim via
  `Sec-WebSocket-Protocol`; service memvalidasi ke User Management (`auth_info`) dan
  mensyaratkan permission `servers.view`. Token tidak boleh di-log.
- Q: Transport SSH memakai apa? → A: `asyncssh` (async-native) dengan PTY interaktif
  (`term_type=xterm-256color`), resize via window si/resize frame. Host key diverifikasi
  dengan pola TOFU: fingerprint disimpan saat koneksi pertama, ditolak jika berubah.
- Q: Apakah ada CRUD inventori? → A: Ya — daftar, detail, buat, ubah, hapus
  (`/api/v1/servers`). Response tidak pernah berisi ciphertext/plaintext kredensial;
  diganti `has_credential` boolean.

### Session 2026-09-29

- Clarification: passphrase untuk private key harus dienkripsi di dalam payload
  credential AES-GCM yang sama. Credential lama yang ciphertext plaintext-nya berupa
  password/private key tanpa wrapper tetap dibaca dengan `passphrase=None`; API
  response dan log tetap tidak mengungkapkan keduanya.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Manage Remote Server Inventory (Priority: P1)

As an operator, I can create, list, read, update, and delete Remote Servers so that the
platform holds an up-to-date inventory of VPS endpoints I manage.

**Why this priority**: The inventory is the prerequisite for opening any console.

**Independent Test**: Create two Remote Servers (password and public-key), list them,
read one detail, update metadata, and delete one; verify no payload or response contains
credential plaintext or ciphertext.

**Acceptance Scenarios**:

1. **Given** name, host, port, username, access method, and a credential, **When** the
   server is created, **Then** it gets a stable identifier and returns `has_credential=true`
   without revealing the secret.
2. **Given** a saved server, **When** its non-secret metadata is updated, **Then** the
   credential stays intact if no new secret is supplied.
3. **Given** a public-key credential, **When** the payload contains a raw PEM block,
   **Then** creation is rejected with a validation error (raw secrets are refused).
4. **Given** a deleted server, **When** a console is requested for it, **Then** the
   connection is refused.

---

### User Story 2 - Open a Single Interactive Console (Priority: P1)

As an operator, I can open an interactive terminal for one Remote Server over WebSocket
so that I can run shell commands as if I had SSH'd directly.

**Why this priority**: The console is the core value of the feature.

**Independent Test**: Open a WebSocket for a server backed by a disposable local SSH
server; type `echo done\n`, receive the shell output streamed back on the `output` frame,
resize the terminal, then close the socket and verify the SSH channel closes.

**Acceptance Scenarios**:

1. **Given** a valid JWT with `servers.view`, **When** the console WebSocket opens,
   **Then** the server replies `ready` and begins bridging PTY output.
2. **Given** an active console, **When** the client sends `input{data}`, **Then** the
   bytes reach the remote shell and echoed output returns on `output` frames.
3. **Given** a resized terminal, **When** the client sends `resize{cols,rows}`,
   **Then** the remote PTY window size updates and rendering adapts.
4. **Given** a WebSocket disconnect (client or network), **When** it detects the drop,
   **Then** the SSH channel and PTY are closed and the session registry entry is removed.
5. **Given** an encrypted private key and its passphrase, **When** the console connects,
   **Then** LMS decrypts both only in process and supplies the passphrase to asyncssh.

---

### User Story 3 - Enforce Single Active Session with Takeover (Priority: P1)

As an operator, I never collide with another operator typing in the same shell.

**Why this priority**: Two writers in one PTY corrupt the session; one-session-per-server
is the agreed concurrency rule.

**Independent Test**: Open console A, then console B for the same server. B must receive
`conflict`; after A confirms takeover, A is closed and B becomes the active console and
streams output.

**Acceptance Scenarios**:

1. **Given** an active console for server S, **When** another WebSocket opens for S,
   **Then** the new socket receives `conflict{active_since}` and no PTY is created.
2. **Given** the conflicting socket, **When** the client sends `takeover`, **Then** the
   existing console is closed (`closed{reason:"replaced"}`), the new socket gets `ready`,
   and a fresh PTY is created.
3. **Given** a takeover, **When** the old console is closed, **Then** its SSH channel is
   released and the registry tracks exactly one active session.

---

### User Story 4 - Never Leak Secrets (Priority: P1)

As a security-conscious platform, I ensure secrets are never reproducible outside the
connection lifetime.

**Why this priority**: Raw secret rejection is a standing rule of this service.

**Independent Test**: Create a server with a known password and private key, then scan
unit/application logs, HTTP responses, WebSocket frames, and error surfaces for any
occurrence of those secret strings.

**Acceptance Scenarios**:

1. **Given** a created server, **When** its list/detail responses are inspected,
   **Then** neither plaintext nor ciphertext credential bytes appear; only
   `has_credential` and credential metadata show.
2. **Given** a console connect, **When** the connection fails (bad key, refused host),
   **Then** error frames and logs describe the failure without the secret material.
3. **Given** the domain boundary, **When** a raw PEM or plaintext password is passed to
   persistence, **Then** the domain layer raises a validation error before any write.
