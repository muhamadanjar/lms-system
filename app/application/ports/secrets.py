from abc import ABC, abstractmethod
from typing import NewType

SecretValue = NewType("SecretValue", str)


class SecretResolver(ABC):
    @abstractmethod
    async def resolve(self, secret_ref: str) -> SecretValue: ...
