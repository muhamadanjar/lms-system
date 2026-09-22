
import asyncio
import logging
from typing import AsyncIterator, Dict, Iterator
from contextlib import asynccontextmanager, contextmanager

from sqlalchemy import Engine
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import Session

from app.config.config import get_settings
# from app.config.database import DatabaseConfig
from app.core.exceptions import DatabaseError
from app.infrastructure.database.connection import DatabaseConnection

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Registry manager for multiple database connections.
    """
    def __init__(self):
        self.settings = get_settings()
        self.connections: Dict[str, DatabaseConnection] = {}
        
        # Initialize default connection logic
        # Now self.settings.database is a Pydantic model (DatabaseSettings)
        # We need to bridge this with DatabaseConnection
        
        # DatabaseConnection expects (name, config)
        # But our new config is a Pydantic model, not the old DatabaseConfig class.
        # We need to adapt it. 
        # Actually Connection expects an object having .get_database_url(), .engine_kwargs, etc.
        # Our new DatabaseSettings class has these methods!
        
        self.connections["default"] = DatabaseConnection("default", self.settings.database)
            
        self._is_connected = False

    def get_connection(self, db_name: str = "default") -> DatabaseConnection:
        if db_name not in self.connections:
            raise DatabaseError(f"Database '{db_name}' not configured.")
        return self.connections[db_name]

    def get_engine(self, db_name: str = "default") -> Engine:
        return self.get_connection(db_name).get_engine()

    async def get_async_engine(self, db_name: str = "default") -> AsyncEngine:
        return await self.get_connection(db_name).get_async_engine()

    @contextmanager
    def get_session(self, db_name: str = "default") -> Iterator[Session]:
        with self.get_connection(db_name).get_session() as session:
            yield session

    @asynccontextmanager
    async def get_async_session(self, db_name: str = "default") -> AsyncIterator[AsyncSession]:
        async with self.get_connection(db_name).get_async_session() as session:
            yield session

    async def connect(self, db_name: str = None) -> None:
        """Connect all or specific DB."""
        targets = [self.get_connection(db_name)] if db_name else self.connections.values()
        
        for conn in targets:
            try:
                await conn.connect()
                if not await conn.health_check():
                    logger.warning(f"Health check failed for '{conn.name}' after connect.")
            except Exception as e:
                logger.error(f"Failed to connect '{conn.name}': {e}")
                if conn.name == "default":
                    raise

        self._is_connected = True

    async def disconnect(self, db_name: str = None) -> None:
        """Disconnect all or specific DB."""
        targets = [self.get_connection(db_name)] if db_name else self.connections.values()
        
        for conn in targets:
            await conn.disconnect()
            
        if not db_name: # If disconnecting all
            self._is_connected = False
            
    async def health_check(self, db_name: str = "default") -> bool:
        return await self.get_connection(db_name).health_check()
    
    async def create_tables(self, db_name: str = "default") -> None:
        await self.get_connection(db_name).create_tables()

    async def create_async_session(self, db_name: str = "default") -> AsyncSession:
        conn = self.get_connection(db_name)
        return await conn.create_async_session()

    def create_session(self, db_name: str = "default") -> Session:
        conn = self.get_connection(db_name)
        return conn.create_session()
        
    @property
    def is_connected(self) -> bool:
        return self._is_connected

database_manager = DatabaseManager()
