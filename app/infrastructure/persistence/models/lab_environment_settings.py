from typing import Optional
from uuid import UUID

from sqlalchemy import Column, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlmodel import Field

from app.domain.value_objects.content import AccessMethod
from app.infrastructure.persistence.models.base import ContentTable


class LabEnvironmentSettings(ContentTable, table=True):
    __tablename__ = "lab_environment_settings"
    __table_args__ = (UniqueConstraint("section_id", name="uq_lab_settings_section"),)
    section_id: UUID = Field(sa_column=Column(Uuid(), ForeignKey("sections.id", ondelete="CASCADE", name="fk_lab_settings_section_id_sections"), nullable=False, index=True))
    provider: str = Field(max_length=100)
    region: Optional[str] = Field(default=None, max_length=100)
    image: str = Field(max_length=255)
    cpu: int = Field(default=1, sa_type=Integer)
    memory_mb: int = Field(default=1024, sa_type=Integer)
    storage_gb: int = Field(default=10, sa_type=Integer)
    access_method: AccessMethod = Field(sa_column=Column(String(10), nullable=False))
    username: str = Field(max_length=255)
    password_secret_ref: Optional[str] = Field(default=None, max_length=500)
    public_key: Optional[str] = Field(default=None, sa_type=Text)
    private_key_secret_ref: Optional[str] = Field(default=None, max_length=500)
    network_policy: Optional[str] = Field(default=None, sa_type=Text)
    timeout_seconds: int = Field(default=3600, sa_type=Integer)
    cleanup_policy: str = Field(default="DELETE_ON_FINISH", max_length=80)
