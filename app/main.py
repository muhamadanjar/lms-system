import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app import __version__
from app.config.config import get_settings

from contextlib import asynccontextmanager
from app.infrastructure.database.health import router as health_router
from app.infrastructure.database.manager import database_manager
from app.domain.exceptions import DomainError
from app.presentation.exception_handlers import (
    handle_domain_error,
    handle_http_error,
    handle_integrity_error,
    handle_request_validation_error,
)
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from app.presentation.routers.courses import router as courses_router
from app.presentation.routers.modules import router as modules_router
from app.presentation.routers.sections import router as sections_router
from app.presentation.routers.servers import router as servers_router
from app.presentation.websocket.console import get_console_registry, ws_router as console_ws_router

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
    get_console_registry().release_all()

    await database_manager.disconnect()
    logger.info("Database connections closed")
    logger.info("Application closed")

app = FastAPI(title=settings.project_name, version=__version__, debug=settings.debug, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors.allowed_origins,
    allow_methods=settings.cors.allowed_methods,
    allow_headers=settings.cors.allowed_headers,
    allow_credentials=settings.cors.allow_credentials,
)
app.include_router(health_router)
app.include_router(courses_router)
app.include_router(modules_router)
app.include_router(sections_router)
app.include_router(servers_router)
app.include_router(console_ws_router)
app.add_exception_handler(DomainError, handle_domain_error)
app.add_exception_handler(IntegrityError, handle_integrity_error)
app.add_exception_handler(HTTPException, handle_http_error)
app.add_exception_handler(RequestValidationError, handle_request_validation_error)
