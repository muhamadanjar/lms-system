# Course Instructors (assign instructor per course)

Progress: [course-instructors](../progress/course-instructors.md)

## Goal

Satu course boleh memiliki lebih dari satu instructor; assignment dikelola hanya oleh admin.

## Design

Join table `course_instructors` dengan unique constraint `(course_id, user_id)`,
FK ke `courses.id` ON DELETE CASCADE. `user_id` menyimpan ID dari User Management API
(sama seperti `enrollments.user_id`).

Alur: router (admin-only) → `CourseInstructorUseCases.assign` → port
`CourseInstructorRepository` → `SqlModelCourseInstructorRepository`.

## Endpoints

- `POST /api/admin/courses/{course_slug}/instructors` — body `{"user_id"}`.
  201 baru, 409 duplikat, 404 course tidak ada, 403 non-admin.

## Testing

Contract test: assign sukses, duplikat 409, course 404, role instructor/learner 403.
Migration test: kolom + unique pair + rollback.
