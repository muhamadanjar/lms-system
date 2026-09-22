import httpx

from app.application.ports.auth import CurrentUser
from app.infrastructure.database.dependencies import get_uow
from app.infrastructure.persistence.unit_of_work import SqlModelUnitOfWork
from app.main import app
from app.presentation.dependencies.auth import get_current_user


async def test_course_module_section_crud_flow(session):
    user = CurrentUser(id="admin-1", email="admin@example.com", roles=frozenset({"admin"}))

    async def override_uow():
        yield SqlModelUnitOfWork(session=session)

    async def override_user():
        return user

    app.dependency_overrides[get_uow] = override_uow
    app.dependency_overrides[get_current_user] = override_user
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/courses", json={"title": "API Course", "slug": "api-course"})
            assert response.status_code == 201
            course = response.json()["data"]

            response = await client.post("/api/courses/api-course/modules", json={"title": "Module", "slug": "api-module"})
            assert response.status_code == 201

            response = await client.post("/api/courses/api-course/modules/api-module/sections", json={"title": "Section", "slug": "api-section", "body": "Hello"})
            assert response.status_code == 201

            response = await client.patch("/api/courses/api-course", json={"title": "Updated Course"})
            assert response.status_code == 200
            assert response.json()["data"]["title"] == "Updated Course"

            response = await client.get("/api/courses/api-course")
            assert response.status_code == 200
            assert response.json()["data"]["modules"][0]["sections"][0]["slug"] == "api-section"

            response = await client.delete("/api/courses/api-course/modules/api-module/sections/api-section")
            assert response.status_code == 204
            response = await client.delete("/api/courses/api-course")
            assert response.status_code == 204
    finally:
        app.dependency_overrides.clear()
