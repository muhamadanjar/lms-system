from sqlmodel import select

from app.domain.entities.course_lab_access import CourseLabAccess
from app.infrastructure.persistence.models.course import Course
from app.infrastructure.persistence.models.course_lab_access import CourseLabAccess as AccessRow
from app.infrastructure.persistence.models.remote_server import RemoteServer
from app.presentation.schemas.lab_access import CourseLabAccessRead


async def test_lab_access_row_and_response_carry_no_secrets(session):
    course_row = Course(slug="secret-course", title="Secrets", sequence=0)
    server = RemoteServer(name="secret-box", host="10.9.9.9", username="student")
    session.add(course_row)
    session.add(server)
    await session.flush()
    access = CourseLabAccess(user_id="learner-1", course_id=course_row.id, server_id=server.id)
    session.add(
        AccessRow(
            id=access.id, user_id=access.user_id, course_id=access.course_id, server_id=access.server_id,
            state=access.state, created_at=access.created_at, updated_at=access.updated_at,
        )
    )
    await session.flush()
    row = (await session.exec(select(AccessRow))).first()
    assert "hunter2-secret" not in repr(row)
    assert not hasattr(row, "password_secret_ref") and not hasattr(row, "private_key_secret_ref")

    payload = CourseLabAccessRead.model_validate(access, from_attributes=True).model_dump_json()
    for token in ("hunter2-secret", "password", "private", "credential", "secret_ref"):
        assert token not in payload.lower()
    assert str(server.id) in payload
