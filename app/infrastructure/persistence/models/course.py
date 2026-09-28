from typing import Optional
from sqlalchemy import Text
from sqlmodel import Field, SQLModel

from app.infrastructure.persistence.models.base import ContentTable


class Course(ContentTable, table=True):
    __tablename__ = "courses"
    title: str = Field(max_length=255)
    description: Optional[str] = Field(default=None, sa_type=Text)
    sequence: int = Field(default=0)
