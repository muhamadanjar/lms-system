from app.application.ports.secrets import SecretResolver, SecretValue
from app.domain.entities.lab_environment import LabEnvironmentSettings


class LabManagementUseCases:
    def __init__(self, uow_factory, secret_resolver: SecretResolver):
        self.uow_factory = uow_factory
        self.secret_resolver = secret_resolver

    async def create(self, settings: LabEnvironmentSettings) -> LabEnvironmentSettings:
        async with self.uow_factory() as uow:
            result = await uow.labs.create(settings)
            await uow.commit()
            return result

    async def resolve_access_secret(self, settings: LabEnvironmentSettings) -> SecretValue:
        ref = settings.password_secret_ref or settings.private_key_secret_ref
        if ref is None:
            raise ValueError("lab settings do not contain a secret reference")
        return await self.secret_resolver.resolve(ref)
