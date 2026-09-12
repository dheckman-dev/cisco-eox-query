"""HTTP client for the Cisco End-of-Life (EOX) API v5."""

from __future__ import annotations

import logging
from typing import Any, Callable, Iterator, Sequence
from urllib.parse import quote

from cisco_eox_query._base import PaginationError, SupportClient
from cisco_eox_query.constants import DEFAULT_MAX_PAGES
from cisco_eox_query.v5.constants import (
    EOX_ATTRIBS,
    MAX_INPUTS,
    ResponseEncoding,
    SoftwareRelease,
)
from cisco_eox_query.v5.models import EOXRecord, EOXResponse

logger = logging.getLogger(__name__)


class EOXClient(SupportClient):
    """Client for the EOX API v5 (``/supporttools/eox/rest/5/...``).

    Each ``search_*`` method maps to one WADL endpoint and returns an
    :class:`EOXResponse`; the ``iter_*`` variants follow pagination across
    every result.
    """

    API_VERSION = 5

    def _request(self, resource: str, params: dict[str, Any], page: int) -> EOXResponse:
        path = f"/supporttools/eox/rest/{self.API_VERSION}/{resource}/{page}"
        return EOXResponse.model_validate(self._get_json(path, params))

    def _iter_all(
        self,
        request_fn: Callable[..., EOXResponse],
        *args: Any,
        max_pages: int | None = None,
        **kwargs: Any,
    ) -> Iterator[EOXRecord]:
        if max_pages is not None and max_pages < 1:
            raise ValueError("max_pages must be >= 1")
        limit = max_pages if max_pages is not None else DEFAULT_MAX_PAGES
        page = 1
        while True:
            if page > limit:
                raise PaginationError(f"pagination did not terminate after {limit} pages")
            response = request_fn(*args, page=page, **kwargs)
            response.raise_for_error()
            yield from response.records
            last = response.pagination.last_index if response.pagination and response.pagination.last_index else 1
            if page >= last:
                return
            page += 1

    def search_by_dates(
        self,
        start_date: str,
        end_date: str,
        *,
        attribs: str | Sequence[str] | None = None,
        page: int = 1,
        response_encoding: ResponseEncoding = "json",
    ) -> EOXResponse:
        """EOXByDates/{pageIndex}/{startDate}/{endDate}.

        ``attribs`` selects which record dates are matched; see ``EOX_ATTRIBS``.
        """
        _validate_encoding(response_encoding)
        params: dict[str, Any] = {"responseencoding": response_encoding}
        if attribs is not None:
            values = (
                [a.strip() for a in attribs.split(",") if a.strip()]
                if isinstance(attribs, str)
                else list(attribs)
            )
            unknown = [a for a in values if a not in EOX_ATTRIBS]
            if unknown:
                raise ValueError(f"invalid eoxAttrib value(s): {unknown}")
            params["eoxAttrib"] = ",".join(values)
        path = (
            f"/supporttools/eox/rest/{self.API_VERSION}/EOXByDates/{page}/"
            f"{quote(str(start_date), safe='')}/{quote(str(end_date), safe='')}"
        )
        logger.debug("EOXByDates path: %s", path)
        return EOXResponse.model_validate(self._get_json(path, params))

    def iter_dates(
        self,
        start_date: str,
        end_date: str,
        *,
        max_pages: int | None = None,
        **kwargs: Any,
    ) -> Iterator[EOXRecord]:
        return self._iter_all(
            self.search_by_dates, start_date, end_date, max_pages=max_pages, **kwargs
        )

    def search_by_product_ids(
        self,
        product_ids: str | Sequence[str],
        *,
        page: int = 1,
        response_encoding: ResponseEncoding = "json",
    ) -> EOXResponse:
        """EOXByProductID/{pageIndex}/{productIDs}.

        Accepts a comma-separated string or an iterable of up to 20 PIDs.
        Wildcards (``*``) are allowed server-side.
        """
        _validate_encoding(response_encoding)
        ids = _join_inputs(product_ids)
        logger.info("searching EOX by product ID(s): %s", ids)
        path = (
            f"/supporttools/eox/rest/{self.API_VERSION}/EOXByProductID/{page}/"
            f"{quote(ids, safe=',=')}"
        )
        return EOXResponse.model_validate(self._get_json(path, {"responseencoding": response_encoding}))

    def iter_product_ids(
        self, product_ids: str | Sequence[str], *, max_pages: int | None = None, **kwargs: Any
    ) -> Iterator[EOXRecord]:
        return self._iter_all(
            self.search_by_product_ids, product_ids, max_pages=max_pages, **kwargs
        )

    def search_by_serial_numbers(
        self,
        serial_numbers: str | Sequence[str],
        *,
        page: int = 1,
        response_encoding: ResponseEncoding = "json",
    ) -> EOXResponse:
        """EOXBySerialNumber/{pageIndex}/{serialNumbers}.

        Accepts a comma-separated string or an iterable of up to 20 serials.
        """
        _validate_encoding(response_encoding)
        numbers = _join_inputs(serial_numbers)
        logger.info("searching EOX by serial number(s): %s", numbers)
        path = (
            f"/supporttools/eox/rest/{self.API_VERSION}/EOXBySerialNumber/{page}/"
            f"{quote(numbers, safe=',')}"
        )
        return EOXResponse.model_validate(self._get_json(path, {"responseencoding": response_encoding}))

    def iter_serial_numbers(
        self, serial_numbers: str | Sequence[str], *, max_pages: int | None = None, **kwargs: Any
    ) -> Iterator[EOXRecord]:
        return self._iter_all(
            self.search_by_serial_numbers, serial_numbers, max_pages=max_pages, **kwargs
        )

    def search_by_software_releases(
        self,
        *releases: SoftwareRelease,
        page: int = 1,
        response_encoding: ResponseEncoding = "json",
    ) -> EOXResponse:
        """EOXBySWReleaseString/{pageIndex}.

        Each release is a ``"SWversion,OSType"`` string or a tuple
        ``(sw_release, os_type)``; at most 20 are allowed per call.
        """
        _validate_encoding(response_encoding)
        if not releases:
            raise ValueError("at least one software release is required")
        if len(releases) > MAX_INPUTS:
            raise ValueError(f"at most {MAX_INPUTS} software release inputs are allowed")
        logger.info("searching EOX by software release(s): %s", ", ".join(map(str, releases)))
        params: dict[str, Any] = {"responseencoding": response_encoding}
        for index, release in enumerate(releases, start=1):
            params[f"input{index}"] = _format_release(release)
        path = f"/supporttools/eox/rest/{self.API_VERSION}/EOXBySWReleaseString/{page}"
        return EOXResponse.model_validate(self._get_json(path, params))

    def iter_software_releases(
        self, *releases: SoftwareRelease, max_pages: int | None = None, **kwargs: Any
    ) -> Iterator[EOXRecord]:
        return self._iter_all(
            self.search_by_software_releases, *releases, max_pages=max_pages, **kwargs
        )


def _validate_encoding(value: ResponseEncoding) -> None:
    if value not in ("json", "xml"):
        raise ValueError(f"invalid responseencoding: {value}")


def _join_inputs(values: str | Sequence[str]) -> str:
    if isinstance(values, str):
        items = [item.strip() for item in values.split(",") if item.strip()]
    else:
        items = [str(value).strip() for value in values]
    if not items:
        raise ValueError("at least one value is required")
    if len(items) > MAX_INPUTS:
        raise ValueError(f"at most {MAX_INPUTS} values are allowed")
    return ",".join(items)


def _format_release(release: SoftwareRelease) -> str:
    if isinstance(release, str):
        return release
    parts = [str(part) for part in release]
    if not 1 <= len(parts) <= 2:
        raise ValueError("each release must be 'SWversion' or 'SWversion,OSType'")
    return ",".join(parts)