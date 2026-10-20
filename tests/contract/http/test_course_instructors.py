import httpx

from app.application.ports.auth import CurrentUser
from app.infrastructure.database.dependencies import get_uow
from app.infrastructure.persistence.unit_of_work import SqlModelUnitOfWork
from app.main import app
from app.presentation.dependencies.auth import get_current_user

COURSE = "instructor-course"


def _user(user_id: str, roles: tuple[str, ...]) -> CurrentUser:
    return CurrentUser(id=user_id, email=f"{user_id}@example.com", roles=frozenset(roles), permissions=frozenset())


def _as(user: CurrentUser) -> None:
    async def override_user():
        return user

    app.dependency_overrides[get_current_user] = override_user


async def _client(session, user: CurrentUser) -> httpx.AsyncClient:
    async def override_uow():
        yield SqlModelUnitOfWork(session=session)

    app.dependency_overrides[get_uow] = override_uow
    _as(user)
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_assign_instructor_is_admin_only_and_conflicts_on_duplicate(session):
    client = await _client(session, _user("admin-1", ("admin",)))
    try:
        async with client:
            seeded = await client.post("/api/admin/courses", json={"title": "Instructor Course", "slug": COURSE})
            assert seeded.status_code == 201, seeded.text

            first = await client.post(f"/api/admin/courses/{COURSE}/instructors", json={"user_id": "guru-1"})
            assert first.status_code == 201, first.text
            body = first.json()["data"]
            assert body["user_id"] == "guru-1"
            assert body["course_id"]

            duplicate = await client.post(f"/api/admin/courses/{COURSE}/instructors", json={"user_id": "guru-1"})
            assert duplicate.status_code == 409, duplicate.text

            second = await client.post(f"/api/admin/courses/{COURSE}/instructors", json={"user_id": "guru-2"})
            assert second.status_code == 201, second.text

            missing = await client.post("/api/admin/courses/no-such-course/instructors", json={"user_id": "guru-1"})
            assert missing.status_code == 404, missing.text

            for role in ("instructor", "learner"):
                _as(_user(f"{role}-1", (role,)))
                denied = await client.post(f"/api/admin/courses/{COURSE}/instructors", json={"user_id": "guru-3"})
                assert denied.status_code == 403, (role, denied.text)
    finally:
        app.dependency_overrides.clear()
