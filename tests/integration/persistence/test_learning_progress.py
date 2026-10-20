from uuid import uuid4
from sqlmodel import select

from app.domain.entities.collect_task import CollectTask
from app.domain.entities.file import FileMetadata
from app.infrastructure.persistence.models.collect_task import CollectTaskFile as TaskFileRow, Files as FileRow
from app.infrastructure.persistence.models.section_completion import SectionCompletion as SectionCompletionRow
from app.infrastructure.persistence.repositories.learning_progress_repository import SqlModelLearningProgressRepository


async def test_section_completion_is_idempotent_and_collect_task_history_round_trips(session):
    repository = SqlModelLearningProgressRepository(session)
    learner_id = "learner-1"
    section_id = uuid4()

    first = await repository.mark_section_complete(learner_id, section_id)
    duplicate = await repository.mark_section_complete(learner_id, section_id)
    assert first.id == duplicate.id
    assert await repository.section_is_complete(learner_id, section_id)

    task = CollectTask(learner_id=learner_id, section_id=section_id)
    event = task.submit(learner_id, "Submitted answer", ["https://example.org/evidence"])
    await repository.save_task(task, [event])
    loaded = await repository.get_task(learner_id, section_id)
    assert loaded is not None
    assert loaded.history[0].submission_text == "Submitted answer"
    assert loaded.history[0].evidence_urls == ("https://example.org/evidence",)

    rows = await session.exec(select(SectionCompletionRow))
    assert len(rows.all()) == 1


async def test_collect_task_file_links_round_trip_per_submission_history(session):
    repository = SqlModelLearningProgressRepository(session)
    task = CollectTask(learner_id="file-learner", section_id=uuid4())
    file = FileMetadata(original_filename="work.pdf", content_type="application/pdf", size_bytes=12, storage_backend="local", storage_key="ab/filekey", sha256="a" * 64, uploaded_by="file-learner")
    event = task.submit("file-learner", "Attached work", [], [file])

    await repository.save_task(task, [event])
    loaded = await repository.get_task("file-learner", task.section_id)
    assert loaded is not None
    assert loaded.history[0].files[0].id == file.id
    access = await repository.get_file_for_task(file.id)
    assert access is not None
    assert access[0].original_filename == "work.pdf"
    assert access[1] == {"file-learner"}
    assert len((await session.exec(select(FileRow))).all()) == 1
    assert len((await session.exec(select(TaskFileRow))).all()) == 1
