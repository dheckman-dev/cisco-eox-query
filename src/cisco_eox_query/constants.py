"""Constants shared across Cisco EOX API client versions."""

from __future__ import annotations

import httpx

BASE_URL = "https://apix.cisco.com"
TOKEN_URL = "https://id.cisco.com/oauth2/default/v1/token"
DEFAULT_TIMEOUT = httpx.Timeout(30.0)

MAX_REQUESTS_PER_SECOND = 5
MAX_REQUESTS_PER_DAY = 5000

DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 5.0
DEFAULT_MIN_REQUEST_INTERVAL = 0.25

__all__ = [
    "BASE_URL",
    "TOKEN_URL",
    "DEFAULT_TIMEOUT",
    "MAX_REQUESTS_PER_SECOND",
    "MAX_REQUESTS_PER_DAY",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_RETRY_DELAY",
    "DEFAULT_MIN_REQUEST_INTERVAL",
]
