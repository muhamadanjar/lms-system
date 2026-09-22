from app.application.ports.secrets import SecretResolver, SecretValue


class InMemorySecretResolver(SecretResolver):
    """Test/dev adapter; production can replace it with a secret-manager adapter."""

    def __init__(self, values: dict[str, str] | None = None):
        self.values = values or {}

    async def resolve(self, secret_ref: str) -> SecretValue:
        if secret_ref not in self.values:
            raise KeyError(f"secret reference is not configured: {secret_ref}")
        return SecretValue(self.values[secret_ref])
