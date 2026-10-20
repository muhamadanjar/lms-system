# Hapus Endpoint Deprecated (Legacy Compatibility)

Plan: [remove-deprecated-endpoints](./remove-deprecated-endpoints.md)

## Status

Selesai — semua fase plan dijalankan. Menunggu review dan keputusan atas Pertanyaan Terbuka pada plan.

## Perubahan

### Fase 1–3 — Hapus route dan bersihkan composition root

- 62 decorator legacy (`@router.get/post/patch/put/delete`, `deprecated=True`) dihapus dari 10 file `app/presentation/routers/*.py`.
- 10 objek `router = APIRouter(prefix=..., tags=["Legacy Compatibility"])` dihapus dari file yang sama.
- `app/main.py`: import router legacy, 10 pemanggilan `app.include_router(...)`, dan entri tag `Legacy Compatibility` di `OPENAPI_TAGS` dihapus.
- Helper bersama (`can_manage`, `use_cases`, `require_learner_enrollment` dari `courses.py`) tetap ada karena dipakai router admin/learner.

Rincian per file: `quizzes.py` 20, `sections.py` 7, `courses.py` 6, `modules.py` 6, `enrollments.py` 6, `collect_tasks.py` 6, `servers.py` 5, `course_labs.py` 4, `admin_enrollments.py` 1, `learner_enrollments.py` 1.

### Fase 4 — Migrasi contract test

11 file di `tests/contract/http/` dialihkan dari path legacy ke `/api/admin/*` atau `/api/learner/*` sesuai role token masing-masing test. Tidak ada test yang dihapus: tidak ditemukan skenario yang murni duplikat. Aturan pengalihan per path ada di plan (bagian "Migrasi contract test").

### Fase 6 — Latent bug yang tersingkap

- `app/presentation/routers/modules.py`: `get_learner_module` memanggil `ContentCrudUseCases.get_module()` tanpa argumen wajib `include_archived`, sehingga `GET /api/learner/courses/{course_slug}/modules/{module_slug}` selalu gagal `TypeError`. Route learner ini belum pernah tersentuh test selama path legacy masih ada. Diperbaiki dengan `include_archived=True` (lalu tetap 404 bila course/module bukan `PUBLISHED`).

## Verifikasi

- `python -m pytest tests -q`: **225 passed, 2 failed**.
- Dua kegagalan tersebut sudah gagal di `HEAD` sebelum perubahan ini (dibuktikan dengan menjalankan test yang sama pada `git archive HEAD`):
  - `tests/contract/http/test_learning_progress.py::test_collect_task_file_upload_keeps_revision_files_private_and_downloadable` — review oleh instructor mengembalikan 403, bukan 200.
  - `tests/integration/persistence/test_learning_progress.py::test_collect_task_file_links_round_trip_per_submission_history` — `repository.get_file_for_task()` mengembalikan `None`.
  - Keduanya tidak diperbaiki di sini karena di luar scope penghapusan endpoint deprecated.
- `import app.main` berhasil; `app.openapi()` memuat 62 path pengganti dan nol path legacy.
- Pencarian `deprecated=True`, `Legacy Compatibility`, dan referensi router legacy di `app/` menghasilkan nol hasil.

## Limitation

- Konsumen produksi di luar monorepo belum diverifikasi (lihat Pertanyaan Terbuka pada plan). Tidak ada mekanisme `410 Gone`; route lama langsung menjadi 404.
- Alias websocket `/api/v1/servers/{server_id}/console` di `app/presentation/websocket/console.py` masih ada karena tidak pernah ditandai `deprecated=True` (di luar 62 endpoint yang jadi scope).
- Dua test yang sudah gagal sebelum perubahan ini masih merah.
