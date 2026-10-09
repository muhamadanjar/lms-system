# Plan: Quiz snapshot insert order (409 on start sitting)

- Progress: [../../progress/quiz-snapshot-insert-order.md](../../progress/quiz-snapshot-insert-order.md)

## Problem

`POST /api/learner/courses/.../quiz/sittings` selalu 409 (`RESOURCE_CONFLICT`) di Postgres.
Reproduksi langsung: `SqlModelQuizSittingRepository.save_snapshot()` gagal
`ForeignKeyViolationError` — `quiz_sitting_options.sitting_question_id` merujuk baris
`quiz_sitting_questions` yang belum ter-insert.

Akar: model `QuizSittingQuestion` / `QuizSittingOption` tidak punya `relationship()`,
jadi SQLAlchemy unit-of-work tidak mengurutkan insert anak sebelum/sesudah orang tua.
Contract test lolos karena memakai SQLite (FK enforcement off).

409-nya menyesatkan: `handle_integrity_error` memetakan `IntegrityError` → `RESOURCE_CONFLICT`.

## Change

1. `app/infrastructure/persistence/repositories/quiz_sitting_repository.py` — `save_snapshot`:
   flush baris pertanyaan dulu, baru tambah + flush opsi.
2. Regression test `tests/integration/persistence/test_snapshot_insert_order.py`:
   rekam urutan statement INSERT via `before_cursor_execute`, assert pertanyaan sebelum opsi.

## Non-goals

- Tidak ganti response mapping 409.
- Tidak tambah `relationship()` (fix satu titik, semua pemanggil lewat `save_snapshot`).

## Verification

- `pytest tests/integration/persistence tests/contract/http/test_quiz_sittings.py`
- Reproduksi manual `start_or_resume_for_path` ke DB Postgres lokal.
