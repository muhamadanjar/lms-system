from abc import ABC, abstractmethod


class UserDirectoryError(Exception):
    """Base error for user directory lookups."""


class EmailNotFound(UserDirectoryError):
    """No user matches the given email."""


class EmailAmbiguous(UserDirectoryError):
    """More than one user matches the given email."""


class DirectoryUnavailable(UserDirectoryError):
    """The directory cannot be reached or rejected the request."""


class UserDirectory(ABC):
    """Resolves a participant email to its canonical user id.

    Owned by the application layer; infrastructure provides the
    User Management adapter, tests provide fakes.
    """

    @abstractmethod
    async def find_user_id_by_email(self, email: str, authorization: str | None) -> str:
        """Return the canonical user id for an exact email match.

        Raises EmailNotFound, EmailAmbiguous, or DirectoryUnavailable.
        """
        ...
