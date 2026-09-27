import httpx

from app.main import app


def _security_schemes():
    return app.openapi().get("components", {}).get("securitySchemes", {})


def test_openapi_exposes_bearer_security_scheme():
    """Swagger UI needs a securityScheme to render the Authorize button."""
    schemes = _security_schemes()
    assert schemes, "no securitySchemes in OpenAPI"
    bearer = next(
        (scheme for scheme in schemes.values() if scheme.get("scheme") == "bearer"),
        None,
    )
    assert bearer is not None, f"no bearer scheme, got: {schemes}"
    assert bearer.get("type") == "http"


def test_protected_routes_require_bearer_in_docs():
    """Every auth-guarded route must carry a security requirement (lock icon)."""
    spec = app.openapi()
    scheme_names = set(_security_schemes())
    assert scheme_names, "no securitySchemes defined"

    protected = [
        ("get", "/api/courses"),
        ("post", "/api/courses"),
        ("get", "/api/courses/{course_slug}"),
        ("get", "/api/v1/servers"),
        ("post", "/api/v1/servers"),
    ]
    for method, path in protected:
        operation = spec["paths"][path][method]
        assert operation.get("security"), f"{method.upper()} {path} missing security requirement"
        required = {name for entry in operation["security"] for name in entry}
        assert required & scheme_names, f"{method.upper()} {path} not bound to a bearer scheme"


async def test_missing_token_returns_401_without_calling_auth_service():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/courses")
        assert response.status_code == 401
        assert response.json()["error"]["message"] == "Bearer token is required"


async def test_non_bearer_scheme_returns_401():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/courses", headers={"Authorization": "Basic dXNlcjpwYXNz"})
        assert response.status_code == 401
