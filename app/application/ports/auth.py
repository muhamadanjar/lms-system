from dataclasses import dataclass, field
from typing import Protocol, Sequence


@dataclass(frozen=True)
class CurrentUser:
    id: str
    email: str | None = None
    roles: frozenset[str] = field(default_factory=frozenset)
    permissions: frozenset[str] = field(default_factory=frozenset)

    def has_any_role(self, roles: Sequence[str]) -> bool:
        return bool(self.roles.intersection(roles))


class AuthInfoProvider(Protocol):
    async def get_current_user(self, authorization: str) -> CurrentUser: ...
