from app.domain.entities.course_lab_access import CourseLabAccess
from app.infrastructure.persistence.mappers.content_mapper import utc
from app.infrastructure.persistence.models.course_lab_access import CourseLabAccess as AccessRow


def to_course_lab_access(row: AccessRow) -> CourseLabAccess:
    return CourseLabAccess(id=row.id, created_at=utc(row.created_at), updated_at=utc(row.updated_at), user_id=row.user_id, course_id=row.course_id, server_id=row.server_id, state=row.state)
