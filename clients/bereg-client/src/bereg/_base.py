"""Shared synchronous/asynchronous HTTP plumbing.

The class in this module is intentionally dependency-light: it only relies on
``httpx``. It is reused verbatim by the flagship clients in this workspace so
that retry / timeout / error-handling behaviour stays consistent across stores.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Mapping
from types import TracebackType
from typing import Any, Self

import httpx

from .exceptions import HTTPError, NotFoundError, ParseError, RateLimitError, RequestError

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30.0
RETRY_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})


def _retry_after_seconds(response: httpx.Response) -> float | None:
    """Return the number of seconds requested via the ``Retry-After`` header."""
    raw = response.headers.get("Retry-After")
    if not raw:
        return None
    try:
        return max(0.0, float(raw))
    except ValueError:
        return None


class BaseHTTPClient:
    """Common HTTP behaviour shared by the sync and async APIs.

    Subclasses are expected to implement the store specific high-level methods
    on top of :meth:`request` / :meth:`arequest`.
    """

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        max_backoff: float = 30.0,
        headers: Mapping[str, str] | None = None,
        user_agent: str | None = None,
        transport: httpx.BaseTransport | None = None,
        async_transport: httpx.AsyncBaseTransport | None = None,
        verify: bool | str = True,
        trust_env: bool = True,
        follow_redirects: bool = True,
        min_request_interval: float = 0.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max(1, int(max_retries))
        self.backoff_factor = backoff_factor
        self.max_backoff = max_backoff
        self.min_request_interval = max(0.0, min_request_interval)
        self._transport = transport
        self._async_transport = async_transport
        self._verify = verify
        self._trust_env = trust_env
        self._follow_redirects = follow_redirects

        self._headers: dict[str, str] = {
            "User-Agent": user_agent or self.DEFAULT_USER_AGENT,
            "Accept": "application/json, text/plain, */*",
        }
        if headers:
            self._headers.update(dict(headers))

        self._sync_client: httpx.Client | None = None
        self._async_client: httpx.AsyncClient | None = None
        self._last_request_at: float = 0.0

    # ------------------------------------------------------------------ #
    # Client lifecycle
    # ------------------------------------------------------------------ #
    DEFAULT_USER_AGENT = "python-http-client/0.1.0"
    USER_AGENT = "python-http-client/0.1.0"

    @property
    def headers(self) -> dict[str, str]:
        """Return a copy of the default request headers."""
        return dict(self._headers)

    def _sync_http(self) -> httpx.Client:
        if self._sync_client is None or self._sync_client.is_closed:
            self._sync_client = httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout,
                headers=self._headers,
                transport=self._transport,
                verify=self._verify,
                trust_env=self._trust_env,
                follow_redirects=self._follow_redirects,
            )
        return self._sync_client

    def _async_http(self) -> httpx.AsyncClient:
        if self._async_client is None or self._async_client.is_closed:
            self._async_client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers=self._headers,
                transport=self._async_transport,
                verify=self._verify,
                trust_env=self._trust_env,
                follow_redirects=self._follow_redirects,
            )
        return self._async_client

    def close(self) -> None:
        """Close the underlying synchronous HTTP client (if any)."""
        if self._sync_client is not None and not self._sync_client.is_closed:
            self._sync_client.close()

    async def aclose(self) -> None:
        """Close the underlying asynchronous HTTP client (if any)."""
        if self._async_client is not None and not self._async_client.is_closed:
            await self._async_client.aclose()

    def __enter__(self) -> Self:
        self._sync_http()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    async def __aenter__(self) -> Self:
        self._async_http()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    # ------------------------------------------------------------------ #
    # Retry helpers
    # ------------------------------------------------------------------ #
    def _backoff_delay(self, attempt: int, response: httpx.Response | None = None) -> float:
        if response is not None:
            retry_after = _retry_after_seconds(response)
            if retry_after is not None:
                return retry_after
        delay = self.backoff_factor * (2 ** (attempt - 1))
        return float(min(delay, self.max_backoff))

    def _throttle_sync(self) -> None:
        if self.min_request_interval <= 0:
            return
        elapsed = time.monotonic() - self._last_request_at
        remaining = self.min_request_interval - elapsed
        if remaining > 0:
            time.sleep(remaining)

    async def _throttle_async(self) -> None:
        if self.min_request_interval <= 0:
            return
        elapsed = asyncio.get_running_loop().time() - self._last_request_at
        remaining = self.min_request_interval - elapsed
        if remaining > 0:
            await asyncio.sleep(remaining)

    # ------------------------------------------------------------------ #
    # Response handling
    # ------------------------------------------------------------------ #
    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        status = response.status_code
        if status < 400:
            return
        url = str(response.url)
        if status == 404:
            raise NotFoundError(
                "Resource not found", status_code=status, url=url, response=response
            )
        if status == 429:
            raise RateLimitError(
                "Rate limit exceeded", status_code=status, url=url, response=response
            )
        raise HTTPError(f"HTTP {status} for {url}", status_code=status, url=url, response=response)

    # ------------------------------------------------------------------ #
    # Requests
    # ------------------------------------------------------------------ #
    def request(
        self,
        method: str,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        json: Any = None,
        data: Any = None,
        content: Any = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """Perform a synchronous request with retries.

        Relative ``url`` values are resolved against ``base_url``.
        """
        http = self._sync_http()
        last_exc: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            self._throttle_sync()
            self._last_request_at = time.monotonic()
            try:
                response = http.request(
                    method,
                    url,
                    params=params,
                    headers=headers,
                    json=json,
                    data=data,
                    content=content,
                    **kwargs,
                )
            except httpx.TransportError as exc:
                last_exc = exc
                if attempt >= self.max_retries:
                    raise RequestError(
                        f"{method} {url} failed after {attempt} attempts: {exc}",
                        method=method,
                        url=url,
                    ) from exc
                delay = self._backoff_delay(attempt)
                logger.warning(
                    "%s %s failed (%s); retrying in %.2fs [%d/%d]",
                    method,
                    url,
                    exc,
                    delay,
                    attempt,
                    self.max_retries,
                )
                time.sleep(delay)
                continue

            if response.status_code in RETRY_STATUS_CODES and attempt < self.max_retries:
                delay = self._backoff_delay(attempt, response)
                logger.warning(
                    "HTTP %d for %s; retrying in %.2fs [%d/%d]",
                    response.status_code,
                    url,
                    delay,
                    attempt,
                    self.max_retries,
                )
                time.sleep(delay)
                continue

            self._raise_for_status(response)
            return response

        # Only reachable if the loop never returned or raised (defensive).
        raise RequestError(  # pragma: no cover - defensive
            f"{method} {url} failed", method=method, url=url
        ) from last_exc

    async def arequest(
        self,
        method: str,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        json: Any = None,
        data: Any = None,
        content: Any = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """Perform an asynchronous request with retries."""
        http = self._async_http()
        last_exc: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            await self._throttle_async()
            self._last_request_at = asyncio.get_running_loop().time()
            try:
                response = await http.request(
                    method,
                    url,
                    params=params,
                    headers=headers,
                    json=json,
                    data=data,
                    content=content,
                    **kwargs,
                )
            except httpx.TransportError as exc:
                last_exc = exc
                if attempt >= self.max_retries:
                    raise RequestError(
                        f"{method} {url} failed after {attempt} attempts: {exc}",
                        method=method,
                        url=url,
                    ) from exc
                delay = self._backoff_delay(attempt)
                logger.warning(
                    "%s %s failed (%s); retrying in %.2fs [%d/%d]",
                    method,
                    url,
                    exc,
                    delay,
                    attempt,
                    self.max_retries,
                )
                await asyncio.sleep(delay)
                continue

            if response.status_code in RETRY_STATUS_CODES and attempt < self.max_retries:
                delay = self._backoff_delay(attempt, response)
                logger.warning(
                    "HTTP %d for %s; retrying in %.2fs [%d/%d]",
                    response.status_code,
                    url,
                    delay,
                    attempt,
                    self.max_retries,
                )
                await asyncio.sleep(delay)
                continue

            self._raise_for_status(response)
            return response

        raise RequestError(  # pragma: no cover - defensive
            f"{method} {url} failed", method=method, url=url
        ) from last_exc

    # ------------------------------------------------------------------ #
    # JSON helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _decode_json(response: httpx.Response) -> Any:
        try:
            return response.json()
        except ValueError as exc:
            raise ParseError(f"Response for {response.url} is not valid JSON") from exc

    def get_json(self, url: str, **kwargs: Any) -> Any:
        """Perform a GET request and decode the JSON body."""
        return self._decode_json(self.request("GET", url, **kwargs))

    async def aget_json(self, url: str, **kwargs: Any) -> Any:
        """Asynchronous counterpart of :meth:`get_json`."""
        return self._decode_json(await self.arequest("GET", url, **kwargs))
