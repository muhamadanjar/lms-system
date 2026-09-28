from abc import ABC, abstractmethod


class UnitOfWorkPort(ABC):
    courses: object
    modules: object
    sections: object
    lab_access: object
    slugs: object
    servers: object
    quizzes: object
    sittings: object

    @abstractmethod
    async def __aenter__(self): ...

    @abstractmethod
    async def __aexit__(self, exc_type, exc, tb): ...

    @abstractmethod
    async def commit(self) -> None: ...

    @abstractmethod
    async def rollback(self) -> None: ...
