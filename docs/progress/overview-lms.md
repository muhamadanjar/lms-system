# Progress: LMS Overview API

Plan: [docs/plans/overview-lms.md](../plans/overview-lms.md)

- [x] Plan + keputusan terdokumentasi (sesi grilling)
- [x] Contract test merah → hijau (`tests/contract/http/test_lms_overview.py`, 2 test: 403 learner, angka tepat)
- [x] Schema `app/presentation/schemas/lms_overview.py`
- [x] Repository agregat `app/infrastructure/persistence/repositories/lms_overview_repository.py`
- [x] Wire UoW: `UnitOfWorkPort.overviews` + `SqlModelUnitOfWork`
- [x] Router `app/presentation/routers/lms_overview.py` + `main.py`
- [x] `docs/api-roles.md` — baris Overview LMS
- [x] Suite hijau penuh: **225 passed**

## Catatan implementasi

- Test fixture: `SectionContentType.MATERIAL` (bukan TEXT), quiz harus di section `QUIZ`,
  `position` unik per module, `collect_tasks` unique `(learner_id, section_id)` → satu task per learner.
- Pembulatan 1 desimal di repository; nol-safe (ratio 0.0 bila tanpa section published, avg 0.0 bila tanpa attempt).
- Belum disentuh (out of scope): halaman dashboard `courses/overview` (frontend), trend chart, cache.
