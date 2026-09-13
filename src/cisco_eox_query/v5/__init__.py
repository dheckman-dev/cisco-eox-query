"""Cisco EOX API v5 client and models."""

from __future__ import annotations

from cisco_eox_query.v5.client import EOXClient
from cisco_eox_query.v5.constants import EOX_ATTRIBS, OS_TYPES
from cisco_eox_query.v5.models import (
    EOXAPIError,
    EOXErrorInfo,
    EOXRecord,
    EOXResponse,
    MigrationDetails,
    PaginationResponseRecord,
)

__all__ = [
    "EOX_ATTRIBS",
    "OS_TYPES",
    "EOXAPIError",
    "EOXClient",
    "EOXErrorInfo",
    "EOXRecord",
    "EOXResponse",
    "MigrationDetails",
    "PaginationResponseRecord",
]
