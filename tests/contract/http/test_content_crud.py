from uuid import uuid4

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
            assert course["progression_mode"] == "FREE"
            assert course["completion_mode"] == "SELF_LEARNING"

            response = await client.patch("/api/courses/api-course", json={"progression_mode": "SEQUENTIAL", "completion_mode": "ADMIN_REVIEW"})
            assert response.status_code == 200
            assert response.json()["data"]["progression_mode"] == "SEQUENTIAL"
            assert response.json()["data"]["completion_mode"] == "ADMIN_REVIEW"

            response = await client.post("/api/courses/api-course/modules", json={"title": "Module", "slug": "api-module"})
            assert response.status_code == 201

            response = await client.post("/api/courses/api-course/modules/api-module/sections", json={"title": "Section", "slug": "api-section", "body": "Hello"})
            assert response.status_code == 201
            assert response.json()["data"]["requires_pass"] is False
            assert response.json()["data"]["terminal_enabled"] is False
            assert response.json()["data"]["is_preview"] is False
            api_section_path = "/api/courses/api-course/modules/api-module/sections/api-section"
            response = await client.patch(api_section_path, json={"is_preview": True})
            assert response.status_code == 200
            assert response.json()["data"]["is_preview"] is True
            response = await client.get(api_section_path)
            assert response.status_code == 200
            assert response.json()["data"]["is_preview"] is True
            response = await client.patch(api_section_path, json={"terminal_enabled": True})
            assert response.status_code == 422

            lab_task_slug = f"api-lab-task-{uuid4().hex[:8]}"
            lab_task_path = f"/api/courses/api-course/modules/api-module/sections/{lab_task_slug}"
            response = await client.post("/api/courses/api-course/modules/api-module/sections", json={"title": "Lab Task", "slug": lab_task_slug, "position": 1, "content_type": "LAB_TASK", "terminal_enabled": True, "is_preview": True})
            assert response.status_code == 201, response.text
            assert response.json()["data"]["terminal_enabled"] is True
            assert response.json()["data"]["is_preview"] is True
            response = await client.get(lab_task_path)
            assert response.status_code == 200
            assert response.json()["data"]["terminal_enabled"] is True
            response = await client.get("/api/courses/api-course")
            assert response.status_code == 200
            lab_task_sections = response.json()["data"]["modules"][0]["sections"]
            lab_task = next(section for section in lab_task_sections if section["slug"] == lab_task_slug)
            assert lab_task["terminal_enabled"] is True
            assert lab_task["is_preview"] is True
            response = await client.patch(lab_task_path, json={"terminal_enabled": False})
            assert response.status_code == 200
            assert response.json()["data"]["terminal_enabled"] is False
            response = await client.patch(lab_task_path, json={"terminal_enabled": True})
            assert response.status_code == 200
            assert response.json()["data"]["terminal_enabled"] is True
            response = await client.patch(lab_task_path, json={"content_type": "MATERIAL"})
            assert response.status_code == 200
            assert response.json()["data"]["terminal_enabled"] is False

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
