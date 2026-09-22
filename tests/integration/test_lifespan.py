from app.main import app


def test_fastapi_uses_database_lifespan_and_health_router():
    assert app.router.lifespan_context is not None
    assert "/health/db" in app.openapi()["paths"]
