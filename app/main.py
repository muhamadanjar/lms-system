import logging
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app import __version__
from app.config.config import get_settings
from app.presentation.middleware.requestid_middleware import RequestIDMiddleware

from contextlib import asynccontextmanager, suppress
from app.infrastructure.database.health import router as health_router
from app.infrastructure.database.manager import database_manager
from app.infrastructure.persistence.unit_of_work import SqlModelUnitOfWork
from app.infrastructure.storage.dependencies import get_file_storage
from app.application.use_cases.collect_tasks import CollectTaskUseCases
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
from app.presentation.routers.courses import (
    admin_router as admin_courses_router,
    learner_router as learner_courses_router,
)
from app.presentation.routers.course_labs import (
    admin_router as admin_course_labs_router,
    learner_router as learner_course_labs_router,
)
from app.presentation.routers.course_instructors import admin_router as admin_course_instructors_router
from app.presentation.routers.lms_overview import admin_lms_router
from app.presentation.routers.enrollments import (
    admin_router as admin_course_enrollments_router,
    learner_router as learner_course_enrollments_router,
)
from app.presentation.routers.learner_enrollments import learner_router as canonical_learner_enrollments_router
from app.presentation.routers.admin_enrollments import admin_router as canonical_admin_enrollments_router
from app.presentation.routers.modules import (
    admin_router as admin_modules_router,
    learner_router as learner_modules_router,
)
from app.presentation.routers.sections import (
    admin_router as admin_sections_router,
    learner_router as learner_sections_router,
)
from app.presentation.routers.servers import admin_router as admin_servers_router
from app.presentation.routers.quizzes import (
    admin_router as admin_quizzes_router,
    learner_router as learner_quizzes_router,
)
from app.presentation.routers.collect_tasks import (
    admin_files_router,
    admin_router as admin_collect_tasks_router,
    learner_files_router,
    learner_router as learner_collect_tasks_router,
)
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
    upload_cleanup_task = asyncio.create_task(_cleanup_expired_collect_task_uploads())
    app.state.collect_task_upload_cleanup = upload_cleanup_task
    try:
        yield
    finally:
        upload_cleanup_task.cancel()
        with suppress(asyncio.CancelledError):
            await upload_cleanup_task

        logger.info("Application shutting down...")
        get_console_registry().release_all()

        await database_manager.disconnect()
        logger.info("Database connections closed")
        logger.info("Application closed")


async def _cleanup_expired_collect_task_uploads() -> None:
    while True:
        try:
            async with database_manager.get_async_session("default") as session:
                uow = SqlModelUnitOfWork(session=session)
                await CollectTaskUseCases(lambda: uow).cleanup_expired_uploads(get_file_storage())
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning("Expired CollectTask upload cleanup failed")
        await asyncio.sleep(60 * 60)

OPENAPI_TAGS = [
    {"name": "Admin Courses"},
    {"name": "Admin Modules"},
    {"name": "Admin Sections"},
    {"name": "Admin Quizzes"},
    {"name": "Admin Enrollment"},
    {"name": "Admin Course Labs"},
    {"name": "Admin Collect Tasks"},
    {"name": "Admin Files"},
    {"name": "Admin Servers"},
    {"name": "Learner Courses"},
    {"name": "Learner Modules"},
    {"name": "Learner Sections"},
    {"name": "Learner Quizzes"},
    {"name": "Learner Enrollment"},
    {"name": "Learner Course Labs"},
    {"name": "Learner Collect Tasks"},
    {"name": "Learner Files"},
]

app = FastAPI(
    title=settings.project_name,
    version=__version__,
    debug=settings.debug,
    lifespan=lifespan,
    openapi_tags=OPENAPI_TAGS,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors.allowed_origins,
    allow_methods=settings.cors.allowed_methods,
    allow_headers=settings.cors.allowed_headers,
    allow_credentials=settings.cors.allow_credentials,
)
app.add_middleware(RequestIDMiddleware)
app.include_router(health_router)
app.include_router(admin_courses_router)
app.include_router(admin_modules_router)
app.include_router(admin_sections_router)
app.include_router(admin_quizzes_router)
app.include_router(admin_course_enrollments_router)
app.include_router(admin_course_instructors_router)
app.include_router(canonical_admin_enrollments_router)
app.include_router(admin_course_labs_router)
app.include_router(admin_collect_tasks_router)
app.include_router(admin_files_router)
app.include_router(admin_servers_router)
app.include_router(admin_lms_router)
app.include_router(learner_courses_router)
app.include_router(learner_modules_router)
app.include_router(learner_sections_router)
app.include_router(learner_quizzes_router)
app.include_router(learner_course_enrollments_router)
app.include_router(canonical_learner_enrollments_router)
app.include_router(learner_course_labs_router)
app.include_router(learner_collect_tasks_router)
app.include_router(learner_files_router)
app.include_router(console_ws_router)
app.add_exception_handler(DomainError, handle_domain_error)
app.add_exception_handler(IntegrityError, handle_integrity_error)
app.add_exception_handler(HTTPException, handle_http_error)
app.add_exception_handler(RequestValidationError, handle_request_validation_error)
