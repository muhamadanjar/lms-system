import logging
from types import SimpleNamespace

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.presentation.exception_handlers import handle_integrity_error
from app.presentation.middleware.requestid_middleware import RequestIDMiddleware


def test_integrity_error_returns_request_id_and_logs_only_constraint_metadata(caplog):
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)
    original = SimpleNamespace(
        diag=SimpleNamespace(constraint_name="uq_collect_tasks_learner_section"),
        sqlstate="23505",
    )
    integrity_error = IntegrityError("INSERT statement with sensitive values", {}, original)

    @app.get("/integrity-error")
    async def integrity_error_route(request: Request):
        return await handle_integrity_error(request, integrity_error)

    with caplog.at_level(logging.ERROR):
        response = TestClient(app).get("/integrity-error")

    payload = response.json()
    assert response.status_code == 409
    assert payload["error"]["code"] == "RESOURCE_CONFLICT"
    assert payload["error"]["request_id"] == response.headers["X-Request-ID"]
    assert "uq_collect_tasks_learner_section" in caplog.text
    assert "23505" in caplog.text
    assert "sensitive values" not in caplog.text
