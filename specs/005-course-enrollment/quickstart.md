# Quickstart: Course Enrollment validation

**Spec**: specs/005-course-enrollment/spec.md | **Plan**: specs/005-course-enrollment/plan.md

## Run

```bash
pytest tests/unit/domain/test_enrollment.py tests/unit/application/test_enrollment.py -q
pytest tests/integration/persistence/test_enrollment.py -q
pytest tests/contract/http/test_enrollments.py -q
alembic upgrade head && alembic heads
rg -n "progress|grade|role" app/domain/entities/enrollment.py app/infrastructure/persistence/models/enrollment.py || true
```

Expected: all green; single head `0009_course_enrollment`; final `rg` empty (no placeholder fields); `alembic check` clean.

## Manual end-to-end

1. `POST /api/courses/{slug}/enrollments {"user_id":"u1"}` → 201 ENROLLED.
2. `POST` again → 200 same id (no duplicate).
3. `POST /api/courses/{slug}/lab/enroll {"user_id":"u2"}` (never enrolled) → 403 ENROLLMENT_REQUIRED.
4. `POST /api/courses/{slug}/lab/enroll {"user_id":"u1"}` → 201 with server.
5. `POST /api/courses/{slug}/enrollments/u1/withdraw` → 200 WITHDRAWN; lab server free for next learner.
6. `POST /api/courses/{slug}/enrollments {"user_id":"u1"}` → new ENROLLED row, lab requestable again.
7. Complete path: enroll u3 → lab enroll → complete → lab still opens for u3.

## Release note (behavioral)

- Lab enroll now requires live enrollment (403 ENROLLMENT_REQUIRED otherwise). Clients that called lab enroll directly must enroll the course first.
