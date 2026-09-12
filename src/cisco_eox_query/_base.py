"""Shared transport, retries, and OAuth2 client-credentials authentication.

All Cisco Support APIs authenticate with a bearer token obtained from the
Cisco API Console using the client-credentials grant, and are subject to rate
limiting. This base class encapsulates token acquisition/caching/refresh,
request throttling, and retry handling so each versioned API client only
concerns itself with endpoints and models.
"""

from __future__ import annotations

import logging
import time
from http import HTTPStatus
from typing import Any, Self

import httpx

from cisco_eox_query.constants import (
    BASE_URL,
    DEFAULT_MAX_RETRIES,
    DEFAULT_MIN_REQUEST_INTERVAL,
    DEFAULT_RETRY_DELAY,
    DEFAULT_TIMEOUT,
    MAX_REQUESTS_PER_DAY,
    MAX_REQUESTS_PER_SECOND,
    TOKEN_URL,
)

logger = logging.getLogger(__name__)

_RETRYABLE_STATUS_CODES = frozenset(
    {
        HTTPStatus.REQUEST_TIMEOUT,               # 408
        HTTPStatus.TOO_EARLY,                     # 425
        HTTPStatus.TOO_MANY_REQUESTS,             # 429
        HTTPStatus.INTERNAL_SERVER_ERROR,         # 500
        HTTPStatus.BAD_GATEWAY,                   # 502
        HTTPStatus.SERVICE_UNAVAILABLE,           # 503
        HTTPStatus.GATEWAY_TIMEOUT,               # 504
    }
)


class RetryError(Exception):
    """Raised when an API request fails after exhausting all retries."""


class RateLimitError(RetryError):
    """Raised when a rate-limited request fails after exhausting all retries."""


class PaginationError(RetryError):
    """Raised when pagination does not terminate within the page limit."""


def _retry_after_seconds(response: httpx.Response, default: float) -> float:
    value = response.headers.get("Retry-After")
    if value:
        try:
            return max(0.0, float(value))
        except ValueError:
            pass
    return default


class SupportClient:
    """Base client providing authenticated, rate-limit-aware httpx transport.

    Args:
        client_id, client_secret: Cisco API Console credentials used to obtain
            and refresh a bearer token via the client-credentials grant.
        access_token: an already-obtained bearer token (skips token fetch).
        base_url, token_url: service endpoints (defaults are current).
        timeout: per-request httpx timeout.
        max_retries: number of retries for transient failures (HTTP 429/5xx or
            transport errors) before giving up.
        retry_delay: base seconds between retries; the ``Retry-After`` response
            header takes precedence when present.
        min_request_interval: minimum seconds between requests to stay under
            the API's requests-per-second limit (``0`` disables throttling).
        transport: optional httpx transport (used by tests).
    """

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        access_token: str | None = None,
        *,
        base_url: str = BASE_URL,
        token_url: str = TOKEN_URL,
        timeout: httpx.Timeout | float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
        min_request_interval: float = DEFAULT_MIN_REQUEST_INTERVAL,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if access_token is None and (client_id is None or client_secret is None):
            raise ValueError("provide access_token or client_id with client_secret")
        if max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = token_url
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.min_request_interval = min_request_interval
        self._access_token = access_token
        self._token_expiry: float | None = None
        self._next_request_at = 0.0
        self._client = httpx.Client(base_url=base_url, timeout=timeout, transport=transport)
        if self._access_token is None:
            self._fetch_token()

    def _fetch_token(self) -> None:
        logger.debug("requesting access token from %s", self.token_url)
        response = self._request_with_retry(
            "POST",
            self.token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        if response.status_code >= 400:
            logger.error("token request failed with %s: %s", response.status_code, response.text[:300])
        response.raise_for_status()
        try:
            payload = response.json()
        except ValueError as exc:
            raise ValueError(
                f"invalid JSON from token endpoint {self.token_url}: {exc}"
            ) from exc
        if "access_token" not in payload:
            raise ValueError(
                f"token endpoint {self.token_url} returned no access_token "
                f"(HTTP {response.status_code})"
            )
        self._access_token = payload["access_token"]
        expires_in = float(payload.get("expires_in", 3600))
        self._token_expiry = time.monotonic() + expires_in - 300
        logger.info("obtained access token (expires_in=%ss)", expires_in)

    def _ensure_token(self) -> None:
        if self._access_token is None:
            self._fetch_token()
        elif (
            self.client_id is not None
            and self._token_expiry is not None
            and time.monotonic() >= self._token_expiry
        ):
            logger.debug("access token expired, refreshing")
            self._fetch_token()

    def _throttle(self) -> None:
        if self.min_request_interval <= 0:
            return
        now = time.monotonic()
        wait = self._next_request_at - now
        if wait > 0:
            logger.debug("throttling request for %.2fs", wait)
            time.sleep(wait)
        self._next_request_at = time.monotonic() + self.min_request_interval

    def _request_with_retry(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        data: dict[str, str] | None = None,
    ) -> httpx.Response:
        request = self._client.build_request(method, url, params=params, headers=headers, data=data)
        attempts = self.max_retries + 1
        for attempt in range(attempts):
            self._throttle()
            try:
                response = self._client.send(request)
            except httpx.TransportError as exc:
                if attempt >= self.max_retries:
                    raise RetryError(
                        f"request to {url} failed after {self.max_retries} retries: {exc}"
                    ) from exc
                logger.warning(
                    "transport error (attempt %d/%d), retrying in %.1fs: %s",
                    attempt + 1,
                    attempts,
                    self.retry_delay,
                    exc,
                )
                time.sleep(self.retry_delay)
                continue
            if response.status_code not in _RETRYABLE_STATUS_CODES:
                return response
            if attempt >= self.max_retries:
                if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
                    raise RateLimitError(
                        f"exceeded the Cisco API rate limit after {self.max_retries} retries; "
                        f"this is likely the daily limit of {MAX_REQUESTS_PER_DAY} requests/day "
                        f"(or the {MAX_REQUESTS_PER_SECOND} requests/second burst limit); "
                        "please wait and try again later"
                    )
                raise RetryError(
                    f"request to {url} returned HTTP {response.status_code} "
                    f"after {self.max_retries} retries"
                )
            delay = _retry_after_seconds(response, self.retry_delay)
            logger.warning(
                "HTTP %s (attempt %d/%d), retrying in %.1fs",
                response.status_code,
                attempt + 1,
                attempts,
                delay,
            )
            time.sleep(delay)
        raise AssertionError("unreachable")

    def _get_json(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self._ensure_token()
        logger.debug("GET %s params=%s", path, params or {})
        response = self._request_with_retry(
            "GET",
            path,
            params=params or {},
            headers={
                "Authorization": f"Bearer {self._access_token}",
                "Accept": "application/json",
            },
        )
        if response.status_code == HTTPStatus.UNAUTHORIZED and self.client_id is not None:
            logger.warning(
                "GET %s returned %s, refreshing token and retrying once",
                path,
                response.status_code,
            )
            self._fetch_token()
            response = self._request_with_retry(
                "GET",
                path,
                params=params or {},
                headers={
                    "Authorization": f"Bearer {self._access_token}",
                    "Accept": "application/json",
                },
            )
        if response.status_code >= 400:
            logger.error("GET %s failed with %s: %s", path, response.status_code, response.text[:300])
        response.raise_for_status()
        logger.debug("GET %s -> %s (%d bytes)", path, response.status_code, len(response.content))
        try:
            return response.json()
        except ValueError as exc:
            raise ValueError(
                f"invalid JSON response from {path} (HTTP {response.status_code}): {exc}"
            ) from exc

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()