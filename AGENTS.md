# LMS System

@/home/anjar/.codex/RTK.md

<!-- codebase-memory-mcp:start -->
# Codebase Knowledge Graph (codebase-memory-mcp)

This project uses codebase-memory-mcp to maintain a knowledge graph of the codebase.
ALWAYS prefer MCP graph tools over grep/glob/file-search for code discovery.

## Priority Order

1. `search_graph` — find functions, classes, routes, variables by pattern
2. `trace_path` — trace who calls a function or what it calls
3. `get_code_snippet` — read specific function/class source code
4. `query_graph` — run Cypher queries for complex patterns
5. `get_architecture` — high-level project summary

## When to fall back to grep/glob

- Searching for string literals, error messages, or config values
- Searching non-code files such as Dockerfiles, shell scripts, or configs
- When MCP tools return insufficient results
<!-- codebase-memory-mcp:end -->

## Project Purpose

LMS System adalah backend untuk mengelola konten pembelajaran dan assessment:

- `Course` memiliki metadata, lifecycle, dan `Module` yang terurut.
- `Module` mengelompokkan `Chapter` yang terurut.
- `Chapter` memiliki salah satu tipe: text material, knowledge quiz, atau lab quiz.
- Knowledge quiz berisi pilihan ganda dan dapat memiliki satu atau lebih jawaban benar.
- Lab quiz berisi instruksi tugas, kriteria validasi, dan konfigurasi lab/VPS.

Vocabulary canonical yang wajib digunakan untuk kode baru:
`Course`, `Module`, `Chapter`, `TextMaterial`, `KnowledgeQuiz`, `LabQuiz`,
`LabEnvironmentSpecification`, `Question`, dan `Option`.

Router `sections.py` yang ada saat ini adalah transitional/compatibility code. Jangan
menghapus atau mengganti kontraknya tanpa specification, migration plan, dan regression tests.

## Non-Negotiable Rules

1. Domain rules MUST berada di domain entity, value object, aggregate, atau domain service;
   bukan di router, ORM model, Pydantic schema, atau provider client.
2. Dependency MUST mengarah ke dalam: presentation → application → domain. Infrastructure
   mengimplementasikan port milik domain/application.
3. Setiap folder, class, interface, dan package baru MUST memiliki tanggung jawab nyata,
   implementasi aktif, serta consumer aktif. Jangan membuat placeholder architecture.
4. Setiap external dependency MUST mempunyai alasan penggunaan dan consumer yang jelas.
   Gunakan standard library terlebih dahulu dan hapus dependency yang tidak dipakai.
5. Secrets, credential VPS, access token, jawaban benar, dan data learner MUST tidak masuk
   ke log, error response, fixture publik, atau repository history.
6. Perubahan course, ordering, publication, quiz evaluation, atau lab provisioning MUST
   memiliki regression tests.

## Clean Architecture and DDD

Gunakan bounded context utama `Learning Content and Assessment` dengan dependency direction:

```text
HTTP / event consumer
        ↓
Presentation adapters
        ↓
Application use cases
        ↓
Domain: aggregates, entities, value objects, services, ports
        ↑
Infrastructure: database, VPS provider, messaging, clock, identity
```

Aturan layer:

- `domain/` harus pure Python. Tidak boleh import FastAPI, SQLAlchemy/SQLModel, Pydantic
  transport schema, HTTP client, database driver, atau SDK VPS.
- `application/` berisi use case, command/query, DTO, transaction boundary, authorization
  decision, dan port yang dibutuhkan use case. Tidak boleh berisi detail ORM atau HTTP client.
- `infrastructure/` berisi implementasi repository, database mapping, provider client,
  queue, event publisher, dan adapter eksternal. Business rule utama bukan di sini.
- `presentation/` berisi router, request/response schema, dependency injection, auth
  extraction, status code, dan error translation. Router tidak memanipulasi aggregate langsung.
- `main.py` adalah composition root untuk wiring dependency dan app lifecycle.

## Recommended Folder Structure

Bounded context adalah konsep domain, bukan folder wajib. Untuk proyek ini, gunakan layer
langsung di bawah `app/` agar sederhana dan konsisten dengan repository yang sudah ada. Ini
adalah target bertahap; jangan membuat seluruh folder sekaligus. Buat folder hanya ketika ada
feature yang menggunakannya dan setiap folder memiliki consumer aktif.

```text
app/
├── main.py
├── config/                          # Settings, environment, CORS
├── core/                            # Errors, security, middleware yang dipakai lintas context
├── domain/                           # Business rules dan model Learning Content
│   ├── entities/                      # Course, Module, Chapter, content entities
│   ├── aggregates/                    # Aggregate roots dan invariant boundaries
│   ├── value_objects/                 # IDs, ordering, lifecycle, answer policy, lab spec
│   ├── services/                      # Business rules lintas entity
│   ├── repositories/                  # Repository ports
│   └── exceptions.py
├── application/                      # Use cases, commands, queries, DTO, ports
│   ├── commands/                      # Create, update, publish, reorder, submit
│   ├── queries/                       # Read models dan query handlers
│   ├── dto/                           # Use-case input/output DTO
│   ├── ports/                         # Clock, identity, lab, event, transaction
│   └── handlers/                      # Use-case orchestration
├── infrastructure/                    # Implementasi adapter eksternal
│   ├── persistence/                   # ORM models, mappers, repositories
│   ├── database/                      # Engine, session, transaction bootstrap
│   ├── lab/                           # VPS/lab provider adapters
│   ├── events/                        # Event adapters jika benar-benar dipakai
│   └── observability/                 # Logging, metrics, tracing
├── presentation/                      # Delivery adapters
│   └── http/
│       ├── routers/                   # Course, module, chapter, quiz, lab endpoints
│       ├── schemas/                   # HTTP-only Pydantic schemas
│       └── dependencies.py
└── shared/                            # Kernel kecil yang benar-benar lintas domain
    ├── identifiers/
    └── pagination/

tests/
├── unit/domain/
├── unit/application/
├── integration/persistence/
├── integration/lab/
├── contract/http/
└── fixtures/
```

Struktur repository saat ini sudah memiliki `app/domain`, `app/infrastructure/database`, dan
`app/presentation/routers`, sehingga struktur layer langsung di bawah `app/` adalah pilihan
yang disarankan. Pertahankan kode existing yang masih dipakai; rapikan secara bertahap ke
subfolder yang sesuai dan jangan membuat duplicate implementation. Bounded context
`Learning Content and Assessment` tetap menjadi batas konseptual untuk domain rules dan use
case, meskipun tidak diwujudkan sebagai folder `contexts/`.

## Domain Model and Invariants

### Course, Module, and Chapter

- `Course` adalah aggregate root untuk lifecycle dan ordering Module.
- `Module` memiliki Course owner dan ordering Chapter.
- `Chapter` memiliki identity, title, position, availability, publication state, dan content
  type: `TEXT`, `KNOWLEDGE_QUIZ`, atau `LAB_QUIZ`.
- Position MUST unik dan deterministik dalam parent yang sama. Reordering dilakukan melalui
  use case, bukan update field bebas dari router.
- Draft content boleh diedit; published content hanya diubah melalui policy yang dispesifikasikan.

### Text Material

`TextMaterial` menyimpan konten pembelajaran dan metadata publication. Validasi format, ukuran,
sanitization, dan publication policy tidak boleh ditentukan oleh renderer HTTP.

### Knowledge Quiz

- `Question` memiliki `Option` yang stabil dan tidak duplikat.
- Quiz memiliki `AnswerPolicy` untuk single-answer atau multiple-answer.
- Evaluasi jawaban MUST deterministik dan membandingkan set jawaban sesuai policy.
- Correct answer tidak boleh bocor pada response learner.
- Empty correct answer, option di luar question, duplicate option, dan jawaban invalid MUST
  ditolak sebelum persistence atau scoring.
- Scoring, attempts, pass threshold, randomization, dan feedback harus ditentukan dalam
  specification, bukan ditambah diam-diam di handler.

### Lab Quiz and VPS

`LabQuiz` memiliki task instructions, validation criteria, timeout, dan
`LabEnvironmentSpecification`. Specification dapat memuat image, CPU, memory, storage,
network, access mode, TTL, dan cleanup policy, tetapi tidak boleh bergantung pada provider
tertentu.

Semua provisioning MUST melalui port seperti `LabProvisioner`:

```python
from typing import Protocol


class LabProvisioner(Protocol):
    async def provision(self, specification: LabEnvironmentSpecification) -> LabInstance:
        """Provision a validated lab environment."""

    async def cleanup(self, instance: LabInstance) -> None:
        """Release resources when execution fails or expires."""
```

Sebelum provisioning, use case MUST memvalidasi target, image, resource limits, network
policy, credential reference, timeout, dan cleanup behavior. Credential value tidak boleh
masuk ke domain entity, log, atau DTO response. Provisioning harus idempotent atau memiliki
recovery strategy yang terdokumentasi.

## Ports, Interfaces, and Packages

Gunakan `abc.ABC`/`@abstractmethod` atau `typing.Protocol` untuk port yang memiliki lebih dari
satu implementasi atau perlu fake pada test. Contoh port:

- `CourseRepository`, `ModuleRepository`, `ChapterRepository`.
- `UnitOfWork` atau transaction port.
- `LabProvisioner` dan `LabValidator`.
- `IdentityProvider`, `AuthorizationService`, dan `Clock`.
- `EventPublisher` atau `QuizAttemptRepository` ketika use case membutuhkannya.

Gunakan constructor injection atau composition root. Hindari service locator, mutable global
state, import cycle, dan base class besar yang memaksa method tidak relevan.

Dependency baseline saat ini meliputi FastAPI, Pydantic, pydantic-settings, SQLAlchemy,
SQLModel, psycopg2, httpx, dan uvicorn. Tambahkan package baru hanya jika:

1. kebutuhan tidak dapat dipenuhi standard library atau dependency yang telah ada;
2. package memiliki maintenance/security justification;
3. package memiliki owner module dan test coverage; dan
4. requirements serta version policy diperbarui bersama perubahan.

`abc` adalah standard library, bukan dependency tambahan. Jangan menambah library hanya untuk
membuat wrapper yang tidak menambah behavior atau memaksakan pola enterprise.

## API and Persistence Rules

- Router memanggil satu application use case per operasi utama dan menerjemahkan error internal
  menjadi HTTP response yang konsisten.
- Pydantic schema hanya untuk boundary HTTP/event; jangan gunakan sebagai domain entity.
- ORM model hanya untuk persistence; mapping ORM ↔ domain dilakukan di infrastructure.
- Repository query tidak boleh mengandung policy domain yang seharusnya berada di aggregate
  atau domain service.
- API breaking change, quiz semantic change, dan persistence schema change MUST memiliki
  migration/compatibility plan.
- Resource baru mengikuti canonical term. Endpoint lama diberi deprecation path jika sudah
  digunakan client.

## Testing Requirements

Setiap feature/use case wajib memiliki:

- unit tests untuk entity, value object, aggregate invariant, dan domain service;
- application tests menggunakan fake/in-memory port untuk success dan failure path;
- persistence integration tests untuk mapping, transaction, ordering, dan migration;
- lab integration/contract tests dengan fake provider atau sandbox, bukan VPS produksi;
- HTTP contract tests untuk request validation, response shape, auth, dan error mapping.

Minimum regression scenarios:

- Course, Module, dan Chapter tidak memiliki ordering yang konflik.
- Chapter hanya menerima content type yang dikenali.
- Multi-answer quiz mengevaluasi seluruh set jawaban benar.
- Jawaban invalid atau duplicate ditolak.
- Lab dengan resource/image/network invalid tidak pernah diprovision.
- Failure setelah provisioning memicu cleanup atau recovery status yang dapat dilacak.
- Correct answer dan credential tidak bocor ke learner response atau structured log.

## Security and Observability

- Authorization diperiksa di application use case; router hanya mengekstrak identity/context.
- Secrets dibaca dari environment atau secret manager melalui configuration adapter.
- Gunakan correlation/request ID pada operasi HTTP dan external provider.
- Log harus structured dan redact credential, token, answer key, serta lab secret.
- External call harus memiliki timeout, retry policy aman, dan error classification.
- Metrics minimal mencakup request failure, quiz evaluation failure, provisioning latency,
  cleanup failure, dan external provider error.
- Health check tidak menjadi bukti bahwa domain workflow berhasil.

## Development Workflow

Untuk feature baru gunakan urutan:

1. `$speckit-specify` untuk behavior, domain invariants, actor, dan acceptance scenarios.
2. `$speckit-clarify` jika lifecycle, scoring, authorization, atau lab behavior ambigu.
3. `$speckit-plan` untuk architecture, data model, ports/adapters, migrations, dan testing.
4. `$speckit-tasks` untuk task yang dependency-ordered dan dapat diverifikasi.
5. `$speckit-implement` untuk implementasi dan verifikasi task.
6. `$speckit-analyze` atau `$speckit-converge` untuk consistency check atau gap audit.

Sebelum mengubah kode:

- baca constitution dan AGENTS.md;
- periksa `git status` dan jangan menimpa perubahan user;
- gunakan codebase-memory MCP: `index_repository` bila belum indexed, lalu `search_graph`,
  `trace_path`, dan `get_code_snippet`;
- gunakan `rg` hanya untuk string literal, konfigurasi, script, atau non-code ketika graph
  tidak mencukupi;
- telusuri inbound/outbound dependency sebelum mengubah public interface.

Saat mengubah kode:

- gunakan `apply_patch` untuk edit file;
- jaga perubahan tetap scoped pada task;
- update tests dan documentation contract dalam perubahan yang sama;
- jangan membuat folder atau interface yang belum memiliki consumer;
- jangan menjalankan `git reset --hard`, `git checkout --`, atau recursive delete tanpa
  instruksi eksplisit dan target yang telah diverifikasi.

Sebelum menyerahkan perubahan:

- jalankan formatter, linter, type checker, import check, dan tests yang tersedia;
- verifikasi dependency direction dan tidak ada import domain ke framework/infrastructure;
- verifikasi migration dan rollback untuk perubahan persistence;
- review log/error response untuk kebocoran secret atau answer key;
- laporkan file berubah, test yang dijalankan, dan limitation yang tersisa.

## Code Style

- Python menggunakan type hints untuk public function, constructor, port, DTO, dan return value.
- Gunakan `snake_case` untuk module/function/variable dan `PascalCase` untuk class.
- Satu class/function memiliki satu tanggung jawab; pecah use case yang terlalu besar.
- Hindari `Any`, mutable global state, hidden I/O, dan catch-all exception tanpa translation.
- Gunakan domain-specific exception dan error code yang dapat dipetakan presentation.
- Docstring wajib untuk port, public use case, aggregate behavior, dan adapter contract yang
  tidak self-explanatory.
- Komentar menjelaskan alasan atau invariant, bukan mengulang isi kode.

## Source of Truth

Prioritas sumber kebenaran:

1. `.specify/memory/constitution.md` untuk governance dan quality gates.
2. `spec.md`, `plan.md`, dan `tasks.md` untuk scope feature aktif.
3. `AGENTS.md` ini untuk implementasi dan vocabulary proyek.
4. Source code dan tests sebagai kondisi implementasi aktual.

Jika sumber kebenaran bertentangan, dokumentasikan konflik, pilih perubahan paling kecil dan
reversible, lalu minta specification atau amendment yang diperlukan.
