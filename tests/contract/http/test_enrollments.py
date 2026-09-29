import httpx

from app.application.ports.auth import CurrentUser
from app.infrastructure.database.dependencies import get_uow
from app.infrastructure.persistence.unit_of_work import SqlModelUnitOfWork
from app.main import app
from app.presentation.dependencies.auth import get_current_user

COURSE = "enrollment-course"


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


async def _seed_course(client: httpx.AsyncClient) -> None:
    response = await client.post("/api/courses", json={"title": "Enrollment Course", "slug": COURSE})
    assert response.status_code == 201, response.text


async def test_enroll_idempotent_and_my_enrollment(session):
    admin = _user("admin-1", roles=("admin",))
    client = await _client(session, admin)
    try:
        async with client:
            await _seed_course(client)
            first = await client.post(f"/api/courses/{COURSE}/enrollments", json={"user_id": "peserta-1"})
            assert first.status_code == 201, first.text
            assert first.json()["data"]["status"] == "ENROLLED"
            second = await client.post(f"/api/courses/{COURSE}/enrollments", json={"user_id": "peserta-1"})
            assert second.status_code in (200, 201)
            assert second.json()["data"]["id"] == first.json()["data"]["id"]

            _as(_user("peserta-1"))
            me = await client.get(f"/api/courses/{COURSE}/enrollments/me")
            assert me.status_code == 200
            assert me.json()["data"]["user_id"] == "peserta-1"
    finally:
        app.dependency_overrides.clear()


async def test_cannot_enroll_other_user_as_learner(session):
    admin = _user("admin-1", roles=("admin",))
    client = await _client(session, admin)
    try:
        async with client:
            await _seed_course(client)
            _as(_user("peserta-1"))
            response = await client.post(f"/api/courses/{COURSE}/enrollments", json={"user_id": "peserta-2"})
            assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


async def test_lab_gate_requires_enrollment(session):
    admin = _user("admin-1", "servers.create", roles=("admin",))
    client = await _client(session, admin)
    try:
        async with client:
            await _seed_course(client)
            response = await client.post(
                "/api/v1/servers",
                json={"name": "gate-box", "host": "10.0.2.9", "username": "u", "credential": {"method": "PASSWORD", "password": "secret"}},
            )
            assert response.status_code == 201, response.text
            denied = await client.post(f"/api/courses/{COURSE}/lab/enroll", json={"user_id": "luar"})
            assert denied.status_code == 403
            assert denied.json()["error"]["code"] == "ENROLLMENT_REQUIRED"
    finally:
        app.dependency_overrides.clear()


async def test_withdraw_releases_lab_and_reenroll(session):
    admin = _user("admin-1", "servers.create", roles=("admin",))
    client = await _client(session, admin)
    try:
        async with client:
            await _seed_course(client)
            response = await client.post(
                "/api/v1/servers",
                json={"name": "reuse-box", "host": "10.0.2.10", "username": "u", "credential": {"method": "PASSWORD", "password": "secret"}},
            )
            assert response.status_code == 201, response.text
            assert (await client.post(f"/api/courses/{COURSE}/enrollments", json={"user_id": "u1"})).status_code == 201
            lab = await client.post(f"/api/courses/{COURSE}/lab/enroll", json={"user_id": "u1"})
            assert lab.status_code == 201, lab.text
            server_id = lab.json()["data"]["server_id"]

            withdrawn = await client.post(f"/api/courses/{COURSE}/enrollments/u1/withdraw")
            assert withdrawn.status_code == 200
            assert withdrawn.json()["data"]["status"] == "WITHDRAWN"

            assert (await client.post(f"/api/courses/{COURSE}/enrollments", json={"user_id": "u2"})).status_code == 201
            lab2 = await client.post(f"/api/courses/{COURSE}/lab/enroll", json={"user_id": "u2"})
            assert lab2.status_code == 201, lab2.text
            assert lab2.json()["data"]["server_id"] == server_id
    finally:
        app.dependency_overrides.clear()


async def test_complete_keeps_lab_access(session):
    admin = _user("admin-1", "servers.create", roles=("admin",))
    client = await _client(session, admin)
    try:
        async with client:
            await _seed_course(client)
            response = await client.post(
                "/api/v1/servers",
                json={"name": "keep-box", "host": "10.0.2.11", "username": "u", "credential": {"method": "PASSWORD", "password": "secret"}},
            )
            assert response.status_code == 201, response.text
            assert (await client.post(f"/api/courses/{COURSE}/enrollments", json={"user_id": "u3"})).status_code == 201
            assert (await client.post(f"/api/courses/{COURSE}/lab/enroll", json={"user_id": "u3"})).status_code == 201
            done = await client.post(f"/api/courses/{COURSE}/enrollments/u3/complete", json={})
            assert done.status_code == 200
            assert done.json()["data"]["status"] == "COMPLETED"
            assert done.json()["data"]["completed_at"]

            _as(_user("u3"))
            mine = await client.get(f"/api/courses/{COURSE}/lab/my-lab")
            assert mine.status_code == 200
            assert mine.json()["data"]["server_id"]
    finally:
        app.dependency_overrides.clear()


class _StubDirectory:
    """Mengganti adapter UM agar contract test tidak butuh service lain."""

    def __init__(self, mapping=None, ambiguous=(), down=False):
        self.mapping = {k.lower(): v for k, v in (mapping or {}).items()}
        self.ambiguous = {a.lower() for a in ambiguous}
        self.down = down

    async def find_user_id_by_email(self, email, authorization):
        from app.application.ports.user_directory import DirectoryUnavailable, EmailAmbiguous, EmailNotFound

        if self.down:
            raise DirectoryUnavailable("down")
        key = email.strip().lower()
        if key in self.ambiguous:
            raise EmailAmbiguous(email)
        if key not in self.mapping:
            raise EmailNotFound(email)
        return self.mapping[key]


def _wire_directory(monkeypatch, directory) -> None:
    from app.presentation.routers import enrollments as enrollments_router

    monkeypatch.setattr(enrollments_router, "_directory", lambda: directory)


async def test_bulk_enroll_207_with_buckets(session, monkeypatch):
    _wire_directory(monkeypatch, _StubDirectory({"a@x.id": "u-email"}))
    admin = _user("admin-1", roles=("admin",))
    client = await _client(session, admin)
    try:
        async with client:
            await _seed_course(client)
            assert (await client.post(f"/api/courses/{COURSE}/enrollments", json={"user_id": "existing"})).status_code == 201
            response = await client.post(
                f"/api/courses/{COURSE}/enrollments/bulk",
                json={"users": [{"user_id": "u1"}, {"user_id": "existing"}, {"user_id": "   "}, {}, {"email": "A@x.id"}]},
            )
            assert response.status_code == 207, response.text
            data = response.json()["data"]
            assert sorted(e["user_id"] for e in data["enrolled"]) == ["u-email", "u1"]
            assert data["skipped"] == [{"identifier": "existing", "reason": "already_enrolled"}]
            assert [f["reason"] for f in data["failed"]] == ["INVALID", "INVALID"]
    finally:
        app.dependency_overrides.clear()


async def test_bulk_enroll_duplicate_within_request(session, monkeypatch):
    _wire_directory(monkeypatch, _StubDirectory())
    admin = _user("admin-1", roles=("admin",))
    client = await _client(session, admin)
    try:
        async with client:
            await _seed_course(client)
            response = await client.post(
                f"/api/courses/{COURSE}/enrollments/bulk",
                json={"users": [{"user_id": "u1"}, {"user_id": "u1"}]},
            )
            assert response.status_code == 207
            assert len(response.json()["data"]["enrolled"]) == 1
            assert response.json()["data"]["skipped"] == [{"identifier": "u1", "reason": "duplicate_in_request"}]
    finally:
        app.dependency_overrides.clear()


async def test_bulk_enroll_email_failures(session, monkeypatch):
    _wire_directory(monkeypatch, _StubDirectory(mapping={}, ambiguous=("dup@x.id",), down=False))
    admin = _user("admin-1", roles=("admin",))
    client = await _client(session, admin)
    try:
        async with client:
            await _seed_course(client)
            response = await client.post(
                f"/api/courses/{COURSE}/enrollments/bulk",
                json={"users": [{"email": "ghost@x.id"}, {"email": "dup@x.id"}, {"user_id": "u9"}]},
            )
            assert response.status_code == 207
            data = response.json()["data"]
            assert {f["identifier"]: f["reason"] for f in data["failed"]} == {"ghost@x.id": "NOT_FOUND", "dup@x.id": "AMBIGUOUS"}
            assert [e["user_id"] for e in data["enrolled"]] == ["u9"]
    finally:
        app.dependency_overrides.clear()


async def test_bulk_enroll_directory_down_only_fails_emails(session, monkeypatch):
    _wire_directory(monkeypatch, _StubDirectory(down=True))
    admin = _user("admin-1", roles=("admin",))
    client = await _client(session, admin)
    try:
        async with client:
            await _seed_course(client)
            response = await client.post(
                f"/api/courses/{COURSE}/enrollments/bulk",
                json={"users": [{"email": "a@x.id"}, {"user_id": "u1"}]},
            )
            assert response.status_code == 207
            data = response.json()["data"]
            assert [e["user_id"] for e in data["enrolled"]] == ["u1"]
            assert data["failed"] == [{"identifier": "a@x.id", "reason": "DIRECTORY_UNAVAILABLE"}]
    finally:
        app.dependency_overrides.clear()


async def test_bulk_denied_for_learner(session, monkeypatch):
    _wire_directory(monkeypatch, _StubDirectory())
    admin = _user("admin-1", roles=("admin",))
    client = await _client(session, admin)
    try:
        async with client:
            await _seed_course(client)
            _as(_user("peserta-1"))
            response = await client.post(f"/api/courses/{COURSE}/enrollments/bulk", json={"users": [{"user_id": "u1"}]})
            assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


async def test_bulk_rejects_over_limit(session, monkeypatch):
    _wire_directory(monkeypatch, _StubDirectory())
    admin = _user("admin-1", roles=("admin",))
    client = await _client(session, admin)
    try:
        async with client:
            await _seed_course(client)
            response = await client.post(
                f"/api/courses/{COURSE}/enrollments/bulk",
                json={"users": [{"user_id": f"u-{i}"} for i in range(101)]},
            )
            assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()
