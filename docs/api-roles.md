# Peran API: Admin vs Peserta

Dokumen hidup pemetaan endpoint × peran di `lms-system`.
Auth: `Authorization: Bearer <JWT User Management>` pada semua endpoint.

Peran:

- **Admin/Pengajar** — `is_superuser` atau role `admin`/`instructor`
  (`require_content_editor`). Mengelola seluruh data course.
- **Peserta** — user terautentikasi role `learner`. Mengambil materi/lab/quiz
  (konten `PUBLISHED` saja; `DRAFT`/`ARCHIVED` hanya editor).
- **Operator VPS** — permission `servers.view|create|update|delete|console`
  (biasanya admin). Mengelola inventori VPS.

## Tabel endpoint × peran

| Area | Endpoint | Admin | Peserta | Catatan |
|---|---|---|---|---|
| Course | `GET /api/courses`, `GET /api/courses/{slug}` | ✅ semua status | ✅ `PUBLISHED` saja | — |
| Course | `POST /api/courses`, `PATCH /{slug}`, `DELETE /{slug}` | ✅ | ❌ | — |
| Module | `GET .../modules`, `GET .../modules/{m}` | ✅ | ✅ `PUBLISHED` saja | — |
| Module | `POST .../modules`, `PUT .../modules/order`, `PATCH /{m}`, `DELETE /{m}` | ✅ | ❌ | Urutan via `/order` |
| Section | `GET .../sections`, `GET .../sections/{s}` | ✅ | ✅ `PUBLISHED` saja (termasuk `body` materi + instruksi lab) | — |
| Section | `POST .../sections`, `PUT .../sections/order`, `PATCH /{s}`, `DELETE /{s}` | ✅ | ❌ | `content_type`: `MATERIAL`, `LAB_TASK`, `QUIZ` |
| Quiz kelola | `PATCH .../sections/{s}/quiz` | ✅ | ❌ 403 | Konfigurasi (exam, attempts, policy) |
| Quiz kelola | `POST .../quiz/questions`, `PATCH .../quiz/questions/{q}` | ✅ | ❌ 403 | Kunci jawaban TIDAK PERNAH keluar di response mana pun |
| Quiz kerjakan | `POST .../quiz/sittings` | ✅ boleh ikut | ✅ | Mulai/lanjut attempt milik sendiri |
| Quiz kerjakan | `PUT /api/quiz-sittings/{id}/answers` | ✅ milik sendiri | ✅ milik sendiri | Ownership dicek (`_owned_sitting`) |
| Quiz kerjakan | `POST /api/quiz-sittings/{id}/finalize`, `GET .../{id}`, `GET .../quiz/result` | ✅ milik sendiri | ✅ milik sendiri | — |
| Enrollment | `POST /api/courses/{slug}/enrollments` | ✅ daftarkan siapa pun | ✅ diri sendiri | Idempoten; `enrolled_at` manual hanya editor |
| Enrollment | `GET .../enrollments/me` | ✅ | ✅ | `null` bila belum terdaftar |
| Enrollment | `GET .../enrollments`, `POST .../{user}/complete` | ✅ | ❌ | Complete = editor saja |
| Enrollment | `POST .../enrollments/bulk` | ✅ maks 100 | ❌ | 207 per-item; `user_id` dan/atau `email` (email di-resolve ke user_id) |
| Enrollment | `POST .../{user}/withdraw` | ✅ siapa pun | ✅ diri sendiri | Withdraw melepas VPS |
| Lab | `GET /api/courses/{slug}/lab/my-lab` | ✅ | ✅ (milik sendiri) | `null` bila belum ada akses |
| Lab | `POST .../lab/enroll` | ✅ daftarkan siapa pun | ✅ diri sendiri | Wajib enrollment aktif → 403 `ENROLLMENT_REQUIRED`; penuh → 409 `CAPACITY_EXHAUSTED` |
| Lab | `DELETE .../lab/release/{user}` | ✅ siapa pun | ✅ diri sendiri | — |
| Lab | `GET .../lab/accesses` | ✅ | ❌ | Daftar akses course |
| VPS | `GET/POST /api/v1/servers`, `GET/PATCH/DELETE /api/v1/servers/{id}` | ✅ permission `servers.*` | ❌ | Response hanya `has_credential`, tanpa secret |
| Console | `WS /api/v1/servers/{id}/console` | ✅ (`servers.view`/`console` atau superuser) | ✅ bila pegang lab access server itu | Satu sesi aktif per server + takeover; JWT via subprotocol `bearer.<token>` |

## Alur 1 — Admin mengelola course

1. Buat course → module → section (`MATERIAL`/`LAB_TASK`/`QUIZ`).
2. Konfigurasi quiz + tambah soal dan jawaban benar.
3. Daftarkan VPS di inventori (`POST /api/v1/servers`).
4. Daftarkan peserta (`POST .../enrollments`), pantau (`GET .../enrollments`, `GET .../lab/accesses`), tandai tuntas (`POST .../{user}/complete`).

```bash
TOKEN=... # JWT admin/instructor
BASE=http://localhost:8000

curl -s -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"title":"Docker Dasar","slug":"docker-dasar"}' $BASE/api/courses

curl -s -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"title":"Modul 1","slug":"modul-1"}' $BASE/api/courses/docker-dasar/modules

curl -s -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"title":"Lab 1","slug":"lab-1","content_type":"LAB_TASK","position":0,"body":"Tugas: ..."}' \
  $BASE/api/courses/docker-dasar/modules/modul-1/sections

curl -s -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"name":"lab-box-1","host":"10.0.0.5","username":"peserta","credential":{"method":"PASSWORD","password":"R4HASIA"}}' \
  $BASE/api/v1/servers

curl -s -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"user_id":"peserta-1"}' $BASE/api/courses/docker-dasar/enrollments

# Bulk: boleh campur user_id dan email (maks 100), jawaban 207 per-item
curl -s -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"users":[{"user_id":"peserta-2"},{"email":"peserta3@contoh.id"},{"email":"salah@alamat.id"}]}' \
  $BASE/api/courses/docker-dasar/enrollments/bulk
# → {"data":{"enrolled":[…],"skipped":[…],"failed":[{"identifier":"salah@alamat.id","reason":"NOT_FOUND"}]}}
```

## Alur 2 — Peserta mengambil materi/lab/quiz

1. Daftar course → baca section `PUBLISHED` → minta lab → buka console → kerjakan quiz.

```bash
TOKEN=... # JWT peserta
BASE=http://localhost:8000
C=$BASE/api/courses/docker-dasar

curl -s -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"user_id":"peserta-1"}' $C/enrollments

curl -s -H "Authorization: Bearer $TOKEN" $C/modules/modul-1/sections/lab-1

curl -s -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"user_id":"peserta-1"}' $C/lab/enroll

curl -s -H "Authorization: Bearer $TOKEN" $C/lab/my-lab

# Console via WebSocket (token sebagai subprotocol "bearer.<JWT>"):
# wscat -c "ws://localhost:8000/api/v1/servers/<server_id>/console" \
#   --subprotocol "bearer.$TOKEN"   # server membalas {"type":"ready"}

curl -s -H "Authorization: Bearer $TOKEN" -X POST \
  $BASE/api/courses/docker-dasar/modules/modul-1/sections/kuis-1/quiz/sittings
```

## Catatan keamanan

- Kunci jawaban quiz dan kredensial VPS tidak pernah muncul di response, log, maupun error.
- Otorisasi write selalu dicek di application use case; router hanya mengekstrak identitas
  (quiz authoring diguard ganda: router + use case).
