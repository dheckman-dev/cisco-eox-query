"""Shared transport and OAuth2 client-credentials authentication.

All Cisco Support APIs authenticate with a bearer token obtained from the
Cisco API Console using the client-credentials grant. This base class
encapsulates token acquisition, caching, and refresh so each versioned API
client only concerns itself with endpoints and models.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Self

import httpx

from cisco_eox_query.constants import BASE_URL, DEFAULT_TIMEOUT, TOKEN_URL

logger = logging.getLogger(__name__)


class SupportClient:
    """Base client providing authenticated httpx transport for Cisco Support APIs."""

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        access_token: str | None = None,
        *,
        base_url: str = BASE_URL,
        token_url: str = TOKEN_URL,
        timeout: httpx.Timeout | float = DEFAULT_TIMEOUT,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if access_token is None and (client_id is None or client_secret is None):
            raise ValueError("provide access_token or client_id with client_secret")
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = token_url
        self._access_token = access_token
        self._token_expiry: float | None = None
        self._client = httpx.Client(base_url=base_url, timeout=timeout, transport=transport)
        if self._access_token is None:
            self._fetch_token()

    def _fetch_token(self) -> None:
        logger.debug("requesting access token from %s", self.token_url)
        response = self._client.post(
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
        payload = response.json()
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

    def _get_json(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self._ensure_token()
        logger.debug("GET %s params=%s", path, params or {})
        response = self._client.get(
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
        return response.json()

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
