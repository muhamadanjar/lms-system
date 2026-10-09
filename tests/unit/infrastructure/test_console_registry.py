from uuid import uuid4

from app.infrastructure.console.registry import InMemoryConsoleRegistry


def test_release_requires_the_active_session_owner():
    registry = InMemoryConsoleRegistry()
    server_id = uuid4()

    assert registry.try_acquire(server_id, "incumbent", session=object()) is True
    assert registry.try_acquire(server_id, "rejected", session=object()) is False
    assert registry.release(server_id, "rejected") is False
    active = registry.active(server_id)
    assert active is not None
    assert active.session_id == "incumbent"
    assert registry.release(server_id, "incumbent") is True
    assert registry.active(server_id) is None
