import pytest

from app.infrastructure.secrets.secret_resolver import InMemorySecretResolver


@pytest.mark.asyncio
async def test_secret_resolver_returns_value_only_for_reference():
    resolver = InMemorySecretResolver({"secret://lab/password": "opaque-value"})
    assert await resolver.resolve("secret://lab/password") == "opaque-value"
    with pytest.raises(KeyError):
        await resolver.resolve("secret://missing")
