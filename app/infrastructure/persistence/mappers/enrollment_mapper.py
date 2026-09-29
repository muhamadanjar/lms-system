from app.domain.entities.enrollment import Enrollment
from app.infrastructure.persistence.mappers.content_mapper import utc
from app.infrastructure.persistence.models.enrollment import Enrollment as EnrollmentRow


def to_enrollment(row: EnrollmentRow) -> Enrollment:
    return Enrollment(
        id=row.id,
        created_at=utc(row.created_at),
        updated_at=utc(row.updated_at),
        user_id=row.user_id,
        course_id=row.course_id,
        status=row.status,
        enrolled_at=utc(row.enrolled_at),
        completed_at=utc(row.completed_at) if row.completed_at else None,
    )
