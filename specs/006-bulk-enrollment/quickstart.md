# Quickstart: Bulk Enrollment validation

**Spec**: specs/006-bulk-enrollment/spec.md | **Plan**: specs/006-bulk-enrollment/plan.md

## Run

```bash
pytest tests/unit/application/test_bulk_enrollment.py tests/unit/infrastructure/test_usermanagement_directory.py -q
pytest tests/contract/http/test_enrollments.py -q
python -c "import app.main; print('import ok')"
```

Expected: all green.

## Manual end-to-end

1. `POST .../enrollments/bulk {"users":[{"user_id":"u1"},{"email":"peserta@x.id"},{"user_id":""}]}` → 207: u1 enrolled, email resolved+enrolled, blank failed INVALID.
2. Repeat same payload → 207: both in skipped `already_enrolled`, nothing duplicated.
3. Unknown email → failed NOT_FOUND; stop UM → email items failed DIRECTORY_UNAVAILABLE, user_id items enrolled.

## Release note

- New editor-only bulk endpoint; single-enroll and lab flows unchanged.
