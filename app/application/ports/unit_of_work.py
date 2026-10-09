from abc import ABC, abstractmethod
from uuid import UUID


class UnitOfWorkPort(ABC):
    courses: object
    modules: object
    sections: object
    lab_access: object
    enrollments: object
    slugs: object
    servers: object
    quizzes: object
    sittings: object
    learning_progress: object
    overviews: object

    @abstractmethod
    async def __aenter__(self): ...

    @abstractmethod
    async def __aexit__(self, exc_type, exc, tb): ...

    @abstractmethod
    async def commit(self) -> None: ...

    @abstractmethod
    async def rollback(self) -> None: ...

    @abstractmethod
    async def lock_collect_task_submission(self, learner_id: str, course_id: UUID) -> None:
        """Serialize submissions from one learner within a course transaction."""
