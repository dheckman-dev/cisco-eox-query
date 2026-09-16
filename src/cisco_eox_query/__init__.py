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
from cisco_eox_query.export import export_to_csv
from cisco_eox_query.v5 import (
    EOX_ATTRIBS,
    EOX_INPUT_TYPE_ALIASES,
    OS_TYPES,
    QUERY_TYPES,
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
    "EOX_ATTRIBS",
    "EOX_INPUT_TYPE_ALIASES",
    "OS_TYPES",
    "QUERY_TYPES",
    "SUPPORTED_API_VERSION",
    "EOXAPIError",
    "EOXClient",
    "EOXErrorInfo",
    "EOXRecord",
    "EOXResponse",
    "MigrationDetails",
    "PaginationError",
    "PaginationResponseRecord",
    "RateLimitError",
    "RetryError",
    "__version__",
    "export_to_csv",
]
