import httpx

from app.main import app

DASHBOARD_ORIGIN = "http://localhost:3000"
# Header yang dikirim axios dashboard (services/dashboard/lib/http.ts).
DASHBOARD_REQUEST_HEADERS = "Authorization,Content-Type,X-Requested-With"


async def test_dashboard_preflight_allows_all_dashboard_headers():
    """Preflight dari dashboard harus lolos: semua header dashboard di-allow.

    Regression: X-Requested-With pernah tidak ada di CORS__ALLOWED_HEADERS
    sehingga browser memblokir semua request dashboard dengan CORS error.
    """
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.options(
            "/api/v1/servers",
            headers={
                "Origin": DASHBOARD_ORIGIN,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": DASHBOARD_REQUEST_HEADERS,
            },
        )
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == DASHBOARD_ORIGIN
        allowed = {h.strip().lower() for h in response.headers["access-control-allow-headers"].split(",")}
        for header in ("authorization", "content-type", "x-requested-with"):
            assert header in allowed, f"{header} missing from {allowed}"
