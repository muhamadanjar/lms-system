from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.domain.exceptions import ConflictError, DomainError, NotFoundError


def _error(request: Request, code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": request.headers.get("X-Request-ID"),
            }
        },
    )


async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
    if isinstance(exc, NotFoundError):
        return _error(request, "RESOURCE_NOT_FOUND", str(exc), 404)
    if isinstance(exc, ConflictError):
        return _error(request, "RESOURCE_CONFLICT", str(exc), 409)
    return _error(request, "VALIDATION_ERROR", str(exc), 422)


async def handle_integrity_error(request: Request, _exc: IntegrityError) -> JSONResponse:
    return _error(request, "RESOURCE_CONFLICT", "The requested change conflicts with existing data", 409)


async def handle_http_error(request: Request, exc: HTTPException) -> JSONResponse:
    code = {
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "RESOURCE_NOT_FOUND",
        503: "AUTH_SERVICE_UNAVAILABLE",
    }.get(exc.status_code, "HTTP_ERROR")
    return _error(request, code, str(exc.detail), exc.status_code)


async def handle_request_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    return _error(request, "REQUEST_VALIDATION_ERROR", str(exc), 422)
