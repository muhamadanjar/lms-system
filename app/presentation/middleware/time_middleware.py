import logging
from time import time
from uuid import uuid4

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class TimingMiddleware(BaseHTTPMiddleware):
    """Adds X-Process-Time header (seconds, 4 decimal places) to every response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time()
        response = await call_next(request)
        response.headers["X-Process-Time"] = f"{time() - start:.4f}s"
        return response
