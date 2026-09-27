from dataclasses import dataclass, field
from typing import Protocol, Sequence


@dataclass(frozen=True)
class CurrentUser:
    id: str
    email: str | None = None
    roles: frozenset[str] = field(default_factory=frozenset)
    permissions: frozenset[str] = field(default_factory=frozenset)
    is_superuser: bool = False

    def has_any_role(self, roles: Sequence[str]) -> bool:
        return bool(self.roles.intersection(roles))

    def has_permission(self, permissions: Sequence[str]) -> bool:
        return bool(self.permissions.intersection(permissions))


class AuthInfoProvider(Protocol):
    async def get_current_user(self, authorization: str) -> CurrentUser: ...
