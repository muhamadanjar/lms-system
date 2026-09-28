"""Console auth re-scoped ke course lab access (TDD US3)."""

from uuid import uuid4

from app.application.ports.auth import CurrentUser
from app.presentation.websocket import console as console_ws


def _learner(user_id="learner-1") -> CurrentUser:
    return CurrentUser(id=user_id, email=f"{user_id}@example.com", roles=frozenset({"learner"}))


def _admin() -> CurrentUser:
    return CurrentUser(id="admin", email="a@example.com", roles=frozenset({"admin"}), is_superuser=True)


class _FakeEnrollment:
    def __init__(self, allowed: set[tuple[str, str]]):
        self.allowed = allowed

    async def user_has_course_server(self, user_id, server_id):
        return (user_id, str(server_id)) in self.allowed


async def test_learner_with_course_access_may_open(monkeypatch):
    server_id = uuid4()
    monkeypatch.setattr(
        "app.application.use_cases.lab_enrollment.LabEnrollmentUseCases",
        lambda _factory: _FakeEnrollment({("learner-1", str(server_id))}),
    )
    assert await console_ws.user_may_open_console(_learner(), server_id) is True


async def test_unrelated_learner_denied(monkeypatch):
    server_id = uuid4()
    monkeypatch.setattr(
        "app.application.use_cases.lab_enrollment.LabEnrollmentUseCases",
        lambda _factory: _FakeEnrollment({("learner-1", str(server_id))}),
    )
    assert await console_ws.user_may_open_console(_learner("learner-2"), server_id) is False


async def test_admin_bypasses_course_check(monkeypatch):
    called = []

    def _factory(factory):
        called.append(factory)
        return _FakeEnrollment(set())

    monkeypatch.setattr("app.application.use_cases.lab_enrollment.LabEnrollmentUseCases", _factory)
    assert await console_ws.user_may_open_console(_admin(), uuid4()) is True
    assert called == []


async def test_enrollment_failure_denies(monkeypatch):
    class _Boom:
        async def user_has_course_server(self, *args):
            raise RuntimeError("db down")

    monkeypatch.setattr("app.application.use_cases.lab_enrollment.LabEnrollmentUseCases", lambda _f: _Boom())
    assert await console_ws.user_may_open_console(_learner(), uuid4()) is False
