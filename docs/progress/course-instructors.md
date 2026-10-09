# Course Instructors (assign instructor per course)

Plan: [course-instructors](./course-instructors.md)

## Status

Done.

## Changes

- `course_instructors` table (migration `0020_course_instructors`): `id`, `user_id`,
  `course_id` (FK `courses.id` CASCADE), `created_at`, `updated_at`, unique
  `(course_id, user_id)` → satu course boleh banyak instructor.
- Domain: entity `CourseInstructor`, port `CourseInstructorRepository`.
- Application: `CourseInstructorUseCases.assign` (resolve course by slug, conflict 409).
- Infrastructure: `SqlModelCourseInstructorRepository`, wired di `SqlModelUnitOfWork`.
- Presentation: `POST /api/admin/courses/{course_slug}/instructors` — admin only
  (`require_roles("admin")`), body `{"user_id": "..."}` → 201, duplikat 409, course tidak ada 404.
- Tests: `tests/contract/http/test_course_instructors.py`, plus registry/migration tests.

## Limitation

Belum ada endpoint list/unassign instructor.
