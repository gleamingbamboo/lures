"""Exception hierarchy for :mod:`flagman`."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import httpx

__all__ = [
    "FlagmanError",
    "HTTPError",
    "NotFoundError",
    "ParseError",
    "RateLimitError",
    "RequestError",
]


class FlagmanError(Exception):
    """Base class for all errors raised by this library."""


class RequestError(FlagmanError):
    """Raised when a request fails at the transport level (no response)."""

    def __init__(self, message: str, *, method: str | None = None, url: str | None = None) -> None:
        super().__init__(message)
        self.method = method
        self.url = url


class HTTPError(FlagmanError):
    """Raised when the server returns an unsuccessful HTTP status code."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        url: str | None = None,
        response: httpx.Response | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.url = url
        self.response = response

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        base = super().__str__()
        if self.status_code is not None:
            return f"{base} (status={self.status_code})"
        return base


class NotFoundError(HTTPError):
    """Raised for HTTP 404 responses."""


class RateLimitError(HTTPError):
    """Raised for HTTP 429 responses."""


class ParseError(FlagmanError):
    """Raised when a response body cannot be decoded into the expected shape."""
