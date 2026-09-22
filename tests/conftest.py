import pytest_asyncio
from sqlmodel import Session, create_engine

from app.infrastructure.persistence.model_registry import metadata


class SyncAsyncSessionAdapter:
    """Async-shaped test adapter around SQLite's synchronous driver."""

    def __init__(self, session: Session):
        self._session = session

    def add(self, instance):
        self._session.add(instance)

    async def exec(self, statement):
        return self._session.exec(statement)

    async def get(self, model, identity):
        return self._session.get(model, identity)

    async def flush(self):
        self._session.flush()

    async def commit(self):
        self._session.commit()

    async def rollback(self):
        self._session.rollback()

    async def delete(self, instance):
        self._session.delete(instance)

    async def execute(self, statement):
        return self._session.execute(statement)

    async def close(self):
        self._session.close()


@pytest_asyncio.fixture
async def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    metadata.create_all(engine)
    db_session = Session(engine)
    yield SyncAsyncSessionAdapter(db_session)
    db_session.close()
    metadata.drop_all(engine)
    engine.dispose()
