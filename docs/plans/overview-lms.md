# Plan: LMS Overview API

Status: approved (keputusan lewat sesi grilling)
Progress: [docs/progress/overview-lms.md](../progress/overview-lms.md)

## Goal

Endpoint statistik untuk halaman **Courses → Overview** di dashboard admin
(`app/(private)/(admin)/courses/overview/page.tsx`, belum ada).

## Keputusan (hasil grilling)

| No | Keputusan | Jawaban |
|----|-----------|---------|
| 1 | Audiens | Admin global (lintas course), bukan per-course / learner |
| 2 | Isi | 6 kartu KPI (tabel di bawah) |
| 3 | Bentuk | Satu endpoint, satu response |
| 4 | Auth | `require_content_editor` (admin + instructor) — pola 50 endpoint lain |
| 5 | Peserta unik | `COUNT(DISTINCT user_id)` semua status; enrollment aktif = `status='ENROLLED'` |
| 6 | Pending review | `collect_tasks.status IN ('SUBMITTED','IN_REVIEW')` |
| 7 | Completion ratio | completions pada section course PUBLISHED ÷ total section course PUBLISHED |
| 8 | Metrik kuis | Rata-rata skor % = `SUM(total_score) ÷ SUM(jumlah soal attempt)` × 100, finalized sittings saja |
| 9 | Path | `GET /api/admin/lms/overview` (prefix terpisah — `/api/admin/courses/overview` ketelan route `/{course_slug}`) |
| 10 | Performa | On-demand aggregate, tanpa cache (cache/counter hanya kalau terbukti lambat) |

## Endpoint

```
GET /api/admin/lms/overview     require_content_editor
200 ApiResponse[LmsOverviewRead]
```

| Field | Definisi |
|-------|----------|
| `total_courses` | `COUNT(courses)` semua status |
| `unique_learners` | `COUNT(DISTINCT enrollments.user_id)` semua status |
| `active_enrollments` | `COUNT(enrollments WHERE status='ENROLLED')` |
| `pending_reviews` | `COUNT(collect_tasks WHERE status IN ('SUBMITTED','IN_REVIEW'))` |
| `section_completion_ratio` | % (float, 1 desimal) completions course-PUBLISHED ÷ section course-PUBLISHED; 0.0 bila denominator 0 |
| `avg_quiz_score_pct` | % (float, 1 desimal) `SUM(total_score) ÷ SUM(quiz_sitting_questions)` atas sittings `total_score IS NOT NULL`; 0.0 bila kosong |

## Desain

Read model murni (tanpa business rule) → ikut pola read endpoint yang sudah ada
(router → repository langsung, lihat `admin_enrollments.py`), bukan use case:

```
presentation/routers/lms_overview.py   # router, auth, response mapping
presentation/schemas/lms_overview.py   # LmsOverviewRead
infrastructure/persistence/repositories/lms_overview_repository.py  # 6 agregat
UnitOfWorkPort + SqlModelUnitOfWork     # tambah atribut `overviews`
main.py                                # include_router
```

## Testing

- `tests/contract/http/test_lms_overview.py`:
  - learner → 403
  - instructor → 200
  - angka tepat dari fixture (2 course, 3 enrollment bermacam status, 2 section published + 1 completion, 4 collect task campur, 1 sitting finalized 3/4)
  - bentuk response: tepat 6 field

## Explicitly out of scope

Trend chart, per-course drilldown, cache/materialized view, permission khusus,
pass-rate per quiz. Semua baru kalau halaman terbukti butuh.
