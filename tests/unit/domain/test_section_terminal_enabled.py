from uuid import uuid4

import pytest

from app.domain.entities.section import Section
from app.domain.exceptions import ValidationError
from app.domain.value_objects.content import SectionContentType, Slug


def test_terminal_is_disabled_by_default():
    section = Section(
        module_id=uuid4(),
        title="Lab task",
        slug=Slug("lab-task"),
        content_type=SectionContentType.LAB_TASK,
    )

    assert section.terminal_enabled is False


def test_section_preview_is_disabled_by_default():
    section = Section(
        module_id=uuid4(),
        title="Material",
        slug=Slug("material-preview"),
        content_type=SectionContentType.MATERIAL,
    )

    assert section.is_preview is False


def test_terminal_cannot_be_enabled_for_non_lab_task_sections():
    with pytest.raises(ValidationError, match="terminal_enabled"):
        Section(
            module_id=uuid4(),
            title="Material",
            slug=Slug("material"),
            content_type=SectionContentType.MATERIAL,
            terminal_enabled=True,
        )
