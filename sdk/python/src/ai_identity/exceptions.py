"""Typed exceptions for the AI Identity SDK."""

from __future__ import annotations


class AIIdentityError(Exception):
    """Base exception for all AI Identity API errors."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        error_code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"message={str(self)!r}, "
            f"status_code={self.status_code}, "
            f"error_code={self.error_code!r})"
        )


class AuthenticationError(AIIdentityError):
    """Raised when the API key is missing or invalid (HTTP 401)."""


class ForbiddenError(AIIdentityError):
    """Raised when the API key lacks permission for this action (HTTP 403)."""


class NotFoundError(AIIdentityError):
    """Raised when the requested resource does not exist (HTTP 404)."""


class ValidationError(AIIdentityError):
    """Raised when request data fails server-side validation (HTTP 422)."""


class RateLimitError(AIIdentityError):
    """Raised when the rate limit is exceeded (HTTP 429)."""
