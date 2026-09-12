"""Constants shared across Cisco EOX API client versions."""

from __future__ import annotations

import httpx

BASE_URL = "https://apix.cisco.com"
TOKEN_URL = "https://id.cisco.com/oauth2/default/v1/token"
DEFAULT_TIMEOUT = httpx.Timeout(30.0)

__all__ = ["BASE_URL", "TOKEN_URL", "DEFAULT_TIMEOUT"]
