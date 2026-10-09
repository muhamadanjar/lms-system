# Progress: Quiz snapshot insert order (409 on start sitting)

- Plan: [../../plans/quiz-snapshot-insert-order.md](../../plans/quiz-snapshot-insert-order.md)

## Status: done

## Log

- [x] Reproduksi: `start_or_resume_for_path` (`quiz-01`, docker-fundamental) → `IntegrityError`
      FK `fk_sitting_options_question` di Postgres lokal (`lms_db`).
- [x] Diagnosa: `save_snapshot` menambah `QuizSittingQuestion` + `QuizSittingOption` dalam
      satu `flush()` tanpa relasi ORM → urutan insert tidak dijamin; SQLite di test tidak menangkap ini.
- [x] Fix: flush pertanyaan sebelum opsi di `quiz_sitting_repository.save_snapshot`.
- [x] Regression test `test_snapshot_insert_order.py` (assert urutan INSERT).
- [x] `pytest tests/integration/persistence tests/contract/http/test_quiz_sittings.py` lulus
      (40); suite penuh `pytest tests -q` → 222 passed.
- [x] Reproduksi ulang ke Postgres: sitting `quiz-01` ter-create.

## Catatan

Quiz lain di DB dev gagal lebih awal dengan `ValidationError` (bukan 409): `kuis-module-1`
punya soal non-MULTICHOICE, `dfdfdfdfdf` SINGLE tanpa tepat satu jawaban benar — data issue
terpisah, bukan bug framework.
