from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_
from sqlmodel import select

from app.application.dto.collect_task_review import CollectTaskReviewEntry
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.entities.collect_task import CollectTask, CollectTaskEvent, CollectTaskStatus
from app.domain.entities.file import FileMetadata
from app.domain.entities.section_completion import SectionCompletion
from app.infrastructure.persistence.models.collect_task import CollectTask as TaskRow, CollectTaskHistory as HistoryRow, CollectTaskFile as TaskFileRow, Files as FileRow
from app.infrastructure.persistence.models.course import Course as CourseRow
from app.infrastructure.persistence.models.module import Module as ModuleRow
from app.infrastructure.persistence.models.section import Section as SectionRow
from app.infrastructure.persistence.models.section_completion import SectionCompletion as CompletionRow


class SqlModelLearningProgressRepository:
    """Persistence adapter for learner section completion and collected lab work."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def mark_section_complete(self, learner_id: str, section_id: UUID) -> SectionCompletion:
        row = (await self.session.exec(select(CompletionRow).where(CompletionRow.learner_id == learner_id, CompletionRow.section_id == section_id))).first()
        if row is None:
            value = SectionCompletion(learner_id=learner_id, section_id=section_id)
            row = CompletionRow(id=value.id, learner_id=value.learner_id, section_id=value.section_id, completed_at=value.completed_at)
            self.session.add(row)
            await self.session.flush()
        return SectionCompletion(learner_id=row.learner_id, section_id=row.section_id, id=row.id, completed_at=row.completed_at)

    async def section_is_complete(self, learner_id: str, section_id: UUID) -> bool:
        return (await self.session.exec(select(CompletionRow.id).where(CompletionRow.learner_id == learner_id, CompletionRow.section_id == section_id))).first() is not None

    async def get_task(self, learner_id: str, section_id: UUID) -> CollectTask | None:
        row = (await self.session.exec(select(TaskRow).where(TaskRow.learner_id == learner_id, TaskRow.section_id == section_id))).first()
        return await self._to_domain(row) if row else None

    async def get_task_by_id(self, task_id: UUID) -> CollectTask | None:
        row = await self.session.get(TaskRow, task_id)
        return await self._to_domain(row) if row else None

    async def save_task(self, task: CollectTask, new_events: list[CollectTaskEvent]) -> CollectTask:
        row = await self.session.get(TaskRow, task.id)
        if row is None:
            row = TaskRow(id=task.id, learner_id=task.learner_id, section_id=task.section_id, status=task.status.value, created_at=task.created_at, updated_at=task.updated_at)
            self.session.add(row)
            # Persist the task before its history rows because these models do not
            # declare ORM relationships for SQLAlchemy to order their inserts.
            await self.session.flush()
        row.status, row.score, row.review_note, row.updated_at = task.status.value, task.score, task.review_note, task.updated_at
        for event in new_events:
            self.session.add(HistoryRow(id=event.id, task_id=task.id, actor_id=event.actor_id, action=event.action, status=event.status.value, submission_text=event.submission_text, evidence_urls=list(event.evidence_urls) or None, score=event.score, review_note=event.review_note, created_at=event.created_at))
            for metadata in event.files:
                if await self.session.get(FileRow, metadata.id) is None:
                    self.session.add(FileRow(id=metadata.id, original_filename=metadata.original_filename, content_type=metadata.content_type, size_bytes=metadata.size_bytes, storage_backend=metadata.storage_backend, storage_key=metadata.storage_key, sha256=metadata.sha256, uploaded_by=metadata.uploaded_by, upload_expires_at=None, created_at=metadata.created_at))
        await self.session.flush()
        for event in new_events:
            for metadata in event.files:
                self.session.add(TaskFileRow(task_id=task.id, file_id=metadata.id, history_id=event.id))
        await self.session.flush()
        return task

    async def save_staged_file(self, metadata: FileMetadata, expires_at: datetime) -> None:
        """Persist uploaded-file metadata before a learner submits the task."""
        self.session.add(FileRow(
            id=metadata.id,
            original_filename=metadata.original_filename,
            content_type=metadata.content_type,
            size_bytes=metadata.size_bytes,
            storage_backend=metadata.storage_backend,
            storage_key=metadata.storage_key,
            sha256=metadata.sha256,
            uploaded_by=metadata.uploaded_by,
            upload_expires_at=expires_at,
            created_at=metadata.created_at,
        ))
        await self.session.flush()

    async def get_staged_files_for_submission(
        self, file_ids: list[UUID], uploaded_by: str, now: datetime
    ) -> list[FileMetadata]:
        if not file_ids:
            return []
        attached_ids = select(TaskFileRow.file_id)
        query = (
            select(FileRow)
            .where(FileRow.id.in_(file_ids))
            .where(FileRow.uploaded_by == uploaded_by)
            .where(FileRow.upload_expires_at > now)
            .where(FileRow.id.not_in(attached_ids))
            .with_for_update()
        )
        rows = (await self.session.exec(query)).all()
        return [_file_metadata(row) for row in rows]

    async def get_staged_file_for_deletion(
        self, file_id: UUID, uploaded_by: str
    ) -> FileMetadata | None:
        attached_ids = select(TaskFileRow.file_id)
        query = (
            select(FileRow)
            .where(FileRow.id == file_id)
            .where(FileRow.uploaded_by == uploaded_by)
            .where(FileRow.upload_expires_at.is_not(None))
            .where(FileRow.id.not_in(attached_ids))
            .with_for_update()
        )
        row = (await self.session.exec(query)).first()
        return _file_metadata(row) if row else None

    async def list_expired_staged_files(self, now: datetime, limit: int = 100) -> list[FileMetadata]:
        attached_ids = select(TaskFileRow.file_id)
        query = (
            select(FileRow)
            .where(FileRow.upload_expires_at <= now)
            .where(FileRow.id.not_in(attached_ids))
            .order_by(FileRow.upload_expires_at, FileRow.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        rows = (await self.session.exec(query)).all()
        return [_file_metadata(row) for row in rows]

    async def delete_staged_file(self, file_id: UUID) -> None:
        row = await self.session.get(FileRow, file_id)
        if row is not None:
            await self.session.delete(row)

    async def list_tasks(self, status: str | None = None) -> list[CollectTask]:
        query = select(TaskRow).order_by(TaskRow.updated_at, TaskRow.id)
        if status:
            query = query.where(TaskRow.status == status)
        return [await self._to_domain(row) for row in (await self.session.exec(query)).all()]

    async def list_tasks_for_review(
        self,
        *,
        statuses: list[str],
        course_id: UUID | None,
        learner_ids: list[str] | None,
        learner_search: str | None,
        course_scope_ids: list[UUID] | None,
        offset: int,
        limit: int,
    ) -> tuple[list[CollectTaskReviewEntry], int]:
        if course_scope_ids is not None and not course_scope_ids:
            return [], 0
        search = learner_search.strip() if learner_search else ""
        if learner_ids is not None and not learner_ids and not search:
            return [], 0

        latest_submission = (
            select(
                HistoryRow.task_id.label("task_id"),
                func.max(HistoryRow.created_at).label("latest_submission_at"),
            )
            .where(HistoryRow.action == "SUBMISSION")
            .group_by(HistoryRow.task_id)
            .subquery()
        )
        filters = [TaskRow.status.in_(statuses)]
        if course_id is not None:
            filters.append(CourseRow.id == course_id)
        if course_scope_ids is not None:
            filters.append(CourseRow.id.in_(course_scope_ids))
        if search and learner_ids:
            filters.append(or_(TaskRow.learner_id.in_(learner_ids), TaskRow.learner_id.ilike(f"%{search}%")))
        elif search:
            filters.append(TaskRow.learner_id.ilike(f"%{search}%"))
        elif learner_ids is not None:
            filters.append(TaskRow.learner_id.in_(learner_ids))

        query = (
            select(TaskRow, SectionRow, ModuleRow, CourseRow, latest_submission.c.latest_submission_at)
            .join(SectionRow, SectionRow.id == TaskRow.section_id)
            .join(ModuleRow, ModuleRow.id == SectionRow.module_id)
            .join(CourseRow, CourseRow.id == ModuleRow.course_id)
            .join(latest_submission, latest_submission.c.task_id == TaskRow.id)
            .where(*filters)
        )
        count_query = (
            select(func.count(TaskRow.id))
            .select_from(TaskRow)
            .join(SectionRow, SectionRow.id == TaskRow.section_id)
            .join(ModuleRow, ModuleRow.id == SectionRow.module_id)
            .join(CourseRow, CourseRow.id == ModuleRow.course_id)
            .join(latest_submission, latest_submission.c.task_id == TaskRow.id)
            .where(*filters)
        )
        total = int((await self.session.exec(count_query)).one())
        rows = (
            await self.session.exec(
                query.order_by(latest_submission.c.latest_submission_at, TaskRow.id)
                .offset(offset)
                .limit(limit)
            )
        ).all()
        entries = []
        for task_row, section_row, module_row, course_row, submitted_at in rows:
            entries.append(
                CollectTaskReviewEntry(
                    task=await self._to_domain(task_row),
                    course_id=course_row.id,
                    course_slug=course_row.slug,
                    course_title=course_row.title,
                    module_slug=module_row.slug,
                    module_title=module_row.title,
                    section_slug=section_row.slug,
                    section_title=section_row.title,
                    latest_submission_at=submitted_at,
                )
            )
        return entries, total

    async def _to_domain(self, row: TaskRow) -> CollectTask:
        history_rows = (await self.session.exec(select(HistoryRow).where(HistoryRow.task_id == row.id).order_by(HistoryRow.created_at, HistoryRow.id))).all()
        links = (await self.session.exec(select(TaskFileRow, FileRow).join(FileRow, FileRow.id == TaskFileRow.file_id).where(TaskFileRow.task_id == row.id))).all()
        files_by_history: dict[UUID, list[FileMetadata]] = {}
        for link, file_row in links:
            files_by_history.setdefault(link.history_id, []).append(_file_metadata(file_row))
        events = [CollectTaskEvent(task_id=item.task_id, id=item.id, actor_id=item.actor_id, action=item.action, status=CollectTaskStatus(item.status), created_at=item.created_at, submission_text=item.submission_text, evidence_urls=tuple(item.evidence_urls or ()), files=tuple(files_by_history.get(item.id, ())), score=item.score, review_note=item.review_note) for item in history_rows]
        return CollectTask(learner_id=row.learner_id, section_id=row.section_id, id=row.id, status=CollectTaskStatus(row.status), score=row.score, review_note=row.review_note, created_at=row.created_at, updated_at=row.updated_at, history=events)

    async def get_file_for_task(self, file_id: UUID) -> tuple[FileMetadata, set[str], set[UUID]] | None:
        query = (
            select(FileRow, TaskRow.learner_id, CourseRow.id)
            .join(TaskFileRow, TaskFileRow.file_id == FileRow.id)
            .join(TaskRow, TaskRow.id == TaskFileRow.task_id)
            .join(SectionRow, SectionRow.id == TaskRow.section_id)
            .join(ModuleRow, ModuleRow.id == SectionRow.module_id)
            .join(CourseRow, CourseRow.id == ModuleRow.course_id)
            .where(FileRow.id == file_id)
        )
        rows = (await self.session.exec(query)).all()
        if not rows:
            return None
        return (
            _file_metadata(rows[0][0]),
            {row[1] for row in rows},
            {row[2] for row in rows},
        )


def _file_metadata(row: FileRow) -> FileMetadata:
    return FileMetadata(id=row.id, original_filename=row.original_filename, content_type=row.content_type, size_bytes=row.size_bytes, storage_backend=row.storage_backend, storage_key=row.storage_key, sha256=row.sha256, uploaded_by=row.uploaded_by, created_at=row.created_at)
