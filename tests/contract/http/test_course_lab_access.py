import httpx

from app.application.ports.auth import CurrentUser
from app.infrastructure.database.dependencies import get_uow
from app.infrastructure.persistence.unit_of_work import SqlModelUnitOfWork
from app.main import app
from app.presentation.dependencies.auth import get_current_user

COURSE = "course-lab-course"
COURSE_B = "course-lab-course-b"


def _user(user_id: str, *permissions: str, roles=("learner",)) -> CurrentUser:
    return CurrentUser(
        id=user_id,
        email=f"{user_id}@example.com",
        roles=frozenset(roles),
        permissions=frozenset(permissions),
    )


async def _client(session, user: CurrentUser):
    async def override_uow():
        yield SqlModelUnitOfWork(session=session)

    async def override_user():
        return user

    app.dependency_overrides[get_uow] = override_uow
    app.dependency_overrides[get_current_user] = override_user
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


def _as(user: CurrentUser):
    async def override_user():
        return user

    app.dependency_overrides[get_current_user] = override_user


async def _seed(client: httpx.AsyncClient, slug: str = COURSE, sections: int = 2, servers: int = 2) -> None:
    tag = slug
    response = await client.post("/api/courses", json={"title": "Course Lab", "slug": slug})
    assert response.status_code == 201, response.text
    response = await client.post(f"/api/courses/{slug}/modules", json={"title": "M", "slug": f"m1-{tag}"})
    assert response.status_code == 201, response.text
    for index in range(sections):
        response = await client.post(
            f"/api/courses/{slug}/modules/m1-{tag}/sections",
            json={"title": f"Lab {index}", "slug": f"lab-{tag}-{index}", "content_type": "LAB_TASK", "position": index, "body": f"Tugas {index}"},
        )
        assert response.status_code == 201, response.text
    for index in range(servers):
        response = await client.post(
            "/api/v1/servers",
            json={"name": f"clab-{tag}-{index}", "host": f"10.0.1.{10 + index}", "username": "peserta", "credential": {"method": "PASSWORD", "password": "secret"}},
        )
        assert response.status_code == 201, response.text


async def _enroll_course(client: httpx.AsyncClient, slug: str, user_id: str) -> None:
    response = await client.post(f"/api/courses/{slug}/enrollments", json={"user_id": user_id})
    assert response.status_code == 201, response.text


async def test_enroll_one_access_shared_across_sections(session):
    admin = _user("admin-1", "servers.create", roles=("admin",))
    client = await _client(session, admin)
    try:
        async with client:
            await _seed(client)
            await _enroll_course(client, COURSE, "peserta-1")
            response = await client.post(f"/api/courses/{COURSE}/lab/enroll", json={"user_id": "peserta-1"})
            assert response.status_code == 201, response.text
            first = response.json()["data"]
            assert first["state"] == "ACTIVE"
            assert first["server_id"]
            assert "section_id" not in first and "queue_position" not in first

            response = await client.post(f"/api/courses/{COURSE}/lab/enroll", json={"user_id": "peserta-1"})
            assert response.status_code in (200, 201)
            assert response.json()["data"]["id"] == first["id"]

            _as(_user("peserta-1"))
            response = await client.get(f"/api/courses/{COURSE}/lab/my-lab")
            assert response.status_code == 200
            assert response.json()["data"]["server_id"] == first["server_id"]
    finally:
        app.dependency_overrides.clear()


async def test_courses_are_isolated(session):
    admin = _user("admin-1", "servers.create", roles=("admin",))
    client = await _client(session, admin)
    try:
        async with client:
            await _seed(client, slug=COURSE, servers=1)
            await _seed(client, slug=COURSE_B, servers=1)
            await _enroll_course(client, COURSE, "peserta-1")
            await _enroll_course(client, COURSE_B, "peserta-1")
            r1 = await client.post(f"/api/courses/{COURSE}/lab/enroll", json={"user_id": "peserta-1"})
            r2 = await client.post(f"/api/courses/{COURSE_B}/lab/enroll", json={"user_id": "peserta-1"})
            assert r1.status_code == 201 and r2.status_code == 201
            assert r1.json()["data"]["server_id"] != r2.json()["data"]["server_id"]
    finally:
        app.dependency_overrides.clear()


async def test_capacity_failure_and_release_reuse(session):
    admin = _user("admin-1", "servers.create", roles=("admin",))
    client = await _client(session, admin)
    try:
        async with client:
            await _seed(client, sections=1, servers=1)
            await _enroll_course(client, COURSE, "u1")
            await _enroll_course(client, COURSE, "u2")
            assert (await client.post(f"/api/courses/{COURSE}/lab/enroll", json={"user_id": "u1"})).status_code == 201
            full = await client.post(f"/api/courses/{COURSE}/lab/enroll", json={"user_id": "u2"})
            assert full.status_code == 409
            assert (await client.delete(f"/api/courses/{COURSE}/lab/release/u1")).status_code == 200
            retry = await client.post(f"/api/courses/{COURSE}/lab/enroll", json={"user_id": "u2"})
            assert retry.status_code == 201
    finally:
        app.dependency_overrides.clear()


async def test_learner_response_has_no_secrets(session):
    admin = _user("admin-1", "servers.create", roles=("admin",))
    client = await _client(session, admin)
    try:
        async with client:
            await _seed(client, sections=1, servers=1)
            await _enroll_course(client, COURSE, "u1")
            response = await client.post(f"/api/courses/{COURSE}/lab/enroll", json={"user_id": "u1"})
            body = response.text.lower()
            assert "secret" not in body
            assert "password" not in body and "private" not in body and "credential" not in body
    finally:
        app.dependency_overrides.clear()
