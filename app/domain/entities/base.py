from datetime import datetime
from typing import Optional, Any
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, model_validator


class BaseEntity(BaseModel):
    id: Optional[UUID] = Field(default_factory=uuid4)
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = Field(default=None)
    is_active: bool = Field(default=True)

    @model_validator(mode='before')
    @classmethod
    def skip_unloaded_relationships(cls, data: Any) -> Any:
        """
        Special validator to handle SQLAlchemy models in async environments.
        It prevents Pydantic from accessing unloaded relationships which would
        trigger a lazy load and cause MissingGreenlet error.
        """
        if not isinstance(data, dict) and hasattr(data, '_sa_instance_state'):
            try:
                from sqlalchemy import inspect
                state = inspect(data)

                # Create a dict with only loaded attributes
                loaded_data = {}
                try:
                    attrs = state.mapper.attrs.keys()
                except Exception:
                    # If mapper inspection fails, return data as-is
                    return data

                for key in attrs:
                    try:
                        if key not in state.unloaded:
                            loaded_data[key] = getattr(data, key)
                    except (AttributeError, Exception):
                        # Skip attributes that can't be accessed
                        continue

                return loaded_data if loaded_data else data
            except Exception:
                # If anything goes wrong, return original data
                return data

        return data

    class Config:
        from_attributes = True # Allow creating from ORM model
