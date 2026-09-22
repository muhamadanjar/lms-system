import pytest

from app.domain.entities.course import Course
from app.domain.entities.lab_environment import LabEnvironmentSettings
from app.domain.entities.module import Module
from app.domain.entities.section import Section
from app.domain.exceptions import ValidationError
from app.domain.value_objects.content import AccessMethod, SectionContentType
from app.infrastructure.persistence.unit_of_work import SqlModelUnitOfWork


async def test_lab_detail_requires_lab_section(session):
    course = Course(slug="material-course", title="Material")
    module = Module(slug="material-module", course_id=course.id, title="Material")
    section = Section(slug="material-section", module_id=module.id, title="Material")
    async with SqlModelUnitOfWork(session=session) as uow:
        await uow.courses.create(course)
        await uow.modules.create(module)
        await uow.sections.create(section)
        with pytest.raises(ValidationError):
            await uow.labs.create(LabEnvironmentSettings(slug="wrong-lab", section_id=section.id, provider="local", image="ubuntu", username="student", access_method=AccessMethod.PASSWORD, password_secret_ref="secret://x"))
