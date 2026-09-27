class DomainError(ValueError):
    """Base exception for invalid learning-content state."""


class ValidationError(DomainError):
    """Raised when an entity or value object violates a domain invariant."""


class ConflictError(DomainError):
    """Raised when a unique business value is already in use."""


class NotFoundError(DomainError):
    """Raised when an expected domain object does not exist."""


class InvalidTransitionError(DomainError):
    """Raised when a status or quiz-attempt transition is not allowed."""


class AuthorizationError(DomainError):
    """Raised when an authenticated actor cannot perform a use case."""
