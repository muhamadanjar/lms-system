"""
Base repository interface definition.
"""
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List, Any
from uuid import UUID

T = TypeVar('T')

class IRepository(Generic[T], ABC):
    """Base repository interface."""

    @abstractmethod
    async def create(self, entity: T) -> T:
        """Create a new entity."""
        pass

    @abstractmethod
    async def get_by_id(self, id: UUID) -> Optional[T]:
        """Get entity by ID."""
        pass

    @abstractmethod
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """Get all entities with pagination."""
        pass

    @abstractmethod
    async def update(self, id: UUID, entity: T) -> Optional[T]:
        """Update an entity."""
        pass

    @abstractmethod
    async def delete(self, id: UUID) -> bool:
        """Delete an entity."""
        pass


class BaseRepository(IRepository[T], ABC):
    """
    Abstract Base Class for repositories.
    Can be used to add domain-specific helper methods on top of IRepository if needed,
    but currently it just mirrors IRepository.
    """
    pass
