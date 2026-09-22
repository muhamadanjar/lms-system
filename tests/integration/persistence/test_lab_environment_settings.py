import pytest

from app.domain.entities.course import Course
from app.domain.entities.lab_environment import LabEnvironmentSettings
from app.domain.entities.module import Module
from app.domain.entities.section import Section
from app.domain.exceptions import ValidationError
from app.domain.value_objects.content import AccessMethod, SectionContentType
from app.infrastructure.persistence.unit_of_work import SqlModelUnitOfWork


async def test_lab_settings_persist_secret_reference_only(session):
    course = Course(slug="lab-course", title="Labs")
    module = Module(slug="lab-module", course_id=course.id, title="Lab Module")
    section = Section(slug="lab-task", module_id=module.id, title="Lab", content_type=SectionContentType.LAB_TASK)
    async with SqlModelUnitOfWork(session=session) as uow:
        await uow.courses.create(course)
        await uow.modules.create(module)
        await uow.sections.create(section)
        settings = LabEnvironmentSettings(slug="lab-settings", section_id=section.id, provider="local", image="ubuntu", username="student", password_secret_ref="secret://lab/password", access_method=AccessMethod.PASSWORD)
        await uow.labs.create(settings)
        await uow.commit()
    loaded = await SqlModelUnitOfWork(session=session).__aenter__()
    try:
        result = await loaded.labs.get_by_section(section.id)
        assert result.password_secret_ref == "secret://lab/password"
    finally:
        await loaded.__aexit__(None, None, None)


def test_lab_settings_reject_raw_private_key():
    with pytest.raises(ValidationError):
        LabEnvironmentSettings(slug="raw-key", section_id=__import__("uuid").uuid4(), provider="local", image="ubuntu", username="student", access_method=AccessMethod.PUBLIC_KEY, public_key="ssh-rsa public", private_key_secret_ref="-----BEGIN PRIVATE KEY-----")
