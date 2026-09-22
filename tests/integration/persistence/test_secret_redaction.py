from sqlmodel import select

from app.domain.entities.course import Course
from app.domain.entities.lab_environment import LabEnvironmentSettings
from app.domain.entities.module import Module
from app.domain.entities.section import Section
from app.domain.value_objects.content import AccessMethod, SectionContentType
from app.infrastructure.persistence.models.lab_environment_settings import LabEnvironmentSettings as LabRow
from app.infrastructure.persistence.unit_of_work import SqlModelUnitOfWork


async def test_raw_secret_is_not_persisted(session):
    course = Course(slug="secret-course", title="Secrets")
    module = Module(slug="secret-module", course_id=course.id, title="Module")
    section = Section(slug="secret-lab", module_id=module.id, title="Lab", content_type=SectionContentType.LAB_TASK)
    async with SqlModelUnitOfWork(session=session) as uow:
        await uow.courses.create(course)
        await uow.modules.create(module)
        await uow.sections.create(section)
        await uow.labs.create(LabEnvironmentSettings(slug="secret-settings", section_id=section.id, provider="local", image="ubuntu", username="student", access_method=AccessMethod.PASSWORD, password_secret_ref="secret://password"))
        await uow.commit()
    row = (await session.exec(select(LabRow))).first()
    assert row.password_secret_ref == "secret://password"
    assert "real-password" not in repr(row)
