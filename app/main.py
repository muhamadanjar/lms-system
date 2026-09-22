import logging
from fastapi import FastAPI
from app.config.config import get_settings

from contextlib import asynccontextmanager
from app.infrastructure.database.health import router as health_router
from app.infrastructure.database.manager import database_manager

settings = get_settings()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting up...")
    try:
        await database_manager.connect()
        logger.info("Database connection initialized")
    except Exception as e:
        logger.error("Failed to initialize database connection: %s", e)
        raise
    yield

    logger.info("Application shutting down...")

    await database_manager.disconnect()
    logger.info("Database connections closed")
    logger.info("Application closed")

app = FastAPI()
