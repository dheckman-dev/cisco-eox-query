"""Client for the Cisco End-of-Life (EOX) API.

Versioning
----------
Library major versions track the EOX API version:

- ``cisco-eox-query`` 1.x implements the EOX API **v5**.
- ``cisco-eox-query`` 2.x will implement the EOX API **v6** (when released).

The versioned implementation lives in :mod:`cisco_eox_query.v5`; this module
re-exports it as the default. Pin an explicit version with::

    from cisco_eox_query.v5 import EOXClient
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from cisco_eox_query._base import PaginationError, RateLimitError, RetryError
from cisco_eox_query.v5 import (
    EOX_ATTRIBS,
    OS_TYPES,
    EOXAPIError,
    EOXClient,
    EOXErrorInfo,
    EOXRecord,
    EOXResponse,
    MigrationDetails,
    PaginationResponseRecord,
)

try:
    __version__ = version("cisco-eox-query")
except PackageNotFoundError:
    __version__ = "1.0.0"

SUPPORTED_API_VERSION = 5

__all__ = [
    "EOXClient",
    "EOXRecord",
    "EOXResponse",
    "EOXErrorInfo",
    "EOXAPIError",
    "MigrationDetails",
    "PaginationResponseRecord",
    "RetryError",
    "RateLimitError",
    "PaginationError",
    "EOX_ATTRIBS",
    "OS_TYPES",
    "SUPPORTED_API_VERSION",
    "__version__",
]