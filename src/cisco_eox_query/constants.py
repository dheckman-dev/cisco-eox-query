"""Constants shared across Cisco EOX API client versions."""

from __future__ import annotations

import httpx

BASE_URL = "https://api.cisco.com"
TOKEN_URL = "https://cloudsso.cisco.com/as/token.oauth2"
DEFAULT_TIMEOUT = httpx.Timeout(30.0)

__all__ = ["BASE_URL", "TOKEN_URL", "DEFAULT_TIMEOUT"]