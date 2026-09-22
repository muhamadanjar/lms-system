"""
Database health check endpoints and utilities.
"""
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from app.infrastructure.database.manager import database_manager

router = APIRouter(prefix="/health", tags=["Health"])


async def get_database_health_status() -> dict:
    """Return the database health payload without an HTTP response wrapper."""
    try:
        is_healthy = await database_manager.health_check()

        return {
            "service": "database",
            "status": "healthy" if is_healthy else "unhealthy",
            "database": "default",
        }
    except Exception as e:
        return {
            "service": "database",
            "status": "unhealthy",
            "error": str(e),
            "database": "default",
        }


@router.get("/db")
async def check_database_health():
    """Check database connection health."""
    health_status = await get_database_health_status()
    response_status = (
        status.HTTP_200_OK
        if health_status["status"] == "healthy"
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )
    return JSONResponse(content=health_status, status_code=response_status)
