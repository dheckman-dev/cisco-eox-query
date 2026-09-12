"""Shared transport and OAuth2 client-credentials authentication.

All Cisco Support APIs authenticate with a bearer token obtained from the
Cisco API Console using the client-credentials grant. This base class
encapsulates token acquisition, caching, and refresh so each versioned API
client only concerns itself with endpoints and models.
"""

from __future__ import annotations

import time
from typing import Any, Self

import httpx

from cisco_eox_query.constants import BASE_URL, DEFAULT_TIMEOUT, TOKEN_URL


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
        response = self._client.post(
            self.token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        payload = response.json()
        self._access_token = payload["access_token"]
        self._token_expiry = time.monotonic() + float(payload.get("expires_in", 3600)) - 300

    def _ensure_token(self) -> None:
        if self._access_token is None:
            self._fetch_token()
        elif (
            self.client_id is not None
            and self._token_expiry is not None
            and time.monotonic() >= self._token_expiry
        ):
            self._fetch_token()

    def _get_json(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self._ensure_token()
        response = self._client.get(
            path,
            params=params or {},
            headers={
                "Authorization": f"Bearer {self._access_token}",
                "Accept": "application/json",
            },
        )
        response.raise_for_status()
        return response.json()

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()