from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, Uuid
from sqlmodel import Field, SQLModel

from app.infrastructure.persistence.models.base import utc_now


class CollectTask(SQLModel, table=True):
    __tablename__ = "collect_tasks"
    __table_args__ = (
        Index("ix_collect_tasks_section_status", "section_id", "status"),
        UniqueConstraint("learner_id", "section_id", name="uq_collect_tasks_learner_section"),
        CheckConstraint("status IN ('SUBMITTED','IN_REVIEW','REVISION_REQUIRED','REVIEWED','PASSED')", name="ck_collect_tasks_status"),
        CheckConstraint("score IS NULL OR (score >= 0 AND score <= 100)", name="ck_collect_tasks_score_range"),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    learner_id: str = Field(max_length=255, index=True)
    section_id: UUID = Field(sa_column=Column(Uuid(), ForeignKey("sections.id", ondelete="CASCADE", name="fk_collect_tasks_section_id_sections"), nullable=False, index=True))
    status: str = Field(default="SUBMITTED", sa_column=Column(String(20), nullable=False))
    score: Optional[int] = Field(default=None, sa_column=Column(Integer, nullable=True))
    review_note: Optional[str] = Field(default=None, sa_type=Text)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class CollectTaskHistory(SQLModel, table=True):
    __tablename__ = "collect_task_history"
    __table_args__ = (CheckConstraint("score IS NULL OR (score >= 0 AND score <= 100)", name="ck_collect_task_history_score_range"),)
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    task_id: UUID = Field(sa_column=Column(Uuid(), ForeignKey("collect_tasks.id", ondelete="CASCADE", name="fk_collect_task_history_task_id_collect_tasks"), nullable=False, index=True))
    actor_id: str = Field(max_length=255)
    action: str = Field(max_length=20)
    status: str = Field(max_length=20)
    submission_text: Optional[str] = Field(default=None, sa_type=Text)
    evidence_urls: Optional[list[str]] = Field(default=None, sa_column=Column(JSON, nullable=True))
    score: Optional[int] = Field(default=None, sa_column=Column(Integer, nullable=True))
    review_note: Optional[str] = Field(default=None, sa_type=Text)
    created_at: datetime = Field(default_factory=utc_now, sa_column=Column(DateTime(timezone=True), nullable=False))


class Files(SQLModel, table=True):
    """File metadata; binary contents live in configured private object storage."""

    __tablename__ = "files"
    __table_args__ = (
        UniqueConstraint("storage_backend", "storage_key", name="uq_files_backend_storage_key"),
        CheckConstraint("size_bytes > 0", name="ck_files_size_positive"),
        CheckConstraint("storage_backend IN ('local','s3')", name="ck_files_storage_backend"),
        Index("ix_files_staged_upload_expiration", "upload_expires_at"),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    original_filename: str = Field(max_length=255)
    content_type: str = Field(max_length=255)
    size_bytes: int = Field(sa_column=Column(Integer, nullable=False))
    storage_backend: str = Field(max_length=16)
    storage_key: str = Field(max_length=512)
    sha256: str = Field(max_length=64)
    uploaded_by: str = Field(max_length=255, index=True)
    upload_expires_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
    created_at: datetime = Field(default_factory=utc_now, sa_column=Column(DateTime(timezone=True), nullable=False))


class CollectTaskFile(SQLModel, table=True):
    """M2M link that keeps each file associated with its immutable submission event."""

    __tablename__ = "collect_task_files"
    __table_args__ = (
        Index("ix_collect_task_files_task_history", "task_id", "history_id"),
        UniqueConstraint("history_id", "file_id", name="uq_collect_task_files_history_file"),
        UniqueConstraint("file_id", name="uq_collect_task_files_file_id"),
    )
    task_id: UUID = Field(sa_column=Column(Uuid(), 
        ForeignKey("collect_tasks.id", ondelete="CASCADE", name="fk_collect_task_files_task_id_collect_tasks"), primary_key=True, nullable=False))
    file_id: UUID = Field(sa_column=Column(Uuid(), ForeignKey("files.id", ondelete="CASCADE", 
        name="fk_collect_task_files_file_id_files"), primary_key=True, nullable=False))
    history_id: UUID = Field(sa_column=Column(Uuid(), ForeignKey("collect_task_history.id", ondelete="CASCADE", name="fk_collect_task_files_history_id_collect_task_history"), primary_key=True, nullable=False))
