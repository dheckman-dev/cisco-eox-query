"""CSV export helpers for :class:`~cisco_eox_query.v5.models.EOXRecord` instances."""

from __future__ import annotations

import csv
import io
import os
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import TextIO

from cisco_eox_query.v5.models import EOXRecord

CSV_COLUMNS: tuple[str, ...] = (
    "EOLProductID",
    "ProductIDDescription",
    "ProductBulletinNumber",
    "LinkToProductBulletinURL",
    "EOXExternalAnnouncementDate",
    "EndOfSaleDate",
    "EndOfSWMaintenanceReleases",
    "EndOfSecurityVulSupportDate",
    "EndOfRoutineFailureAnalysisDate",
    "EndOfServiceContractRenewal",
    "LastDateOfSupport",
    "EndOfSvcAttachDate",
    "UpdatedTimeStamp",
    "QueryType",
    "EOXInputValue",
    "MigrationPIDActiveFlag",
    "MigrationInformation",
    "MigrationOption",
    "MigrationProductId",
    "MigrationProductName",
    "MigrationStrategy",
    "MigrationProductInfoURL",
)


def export_to_csv(
    records: Sequence[EOXRecord],
    output: str | os.PathLike[str] | TextIO | None = None,
) -> str | None:
    """Serialize ``records`` to CSV and return the text or write it to ``output``.

    The header row is always written, even for an empty ``records`` list, so
    the output is always a valid CSV document. Columns follow the flattened
    ``CSV_COLUMNS`` schema:

    - The first 15 columns map directly to ``EOXRecord`` fields; the
      ``QueryType`` column holds the normalized query type
      (e.g. ``queried_product_id``).
    - The seven ``Migration*`` columns map to ``record.migration_details``;
      they are empty cells when ``migration_details`` is ``None``.

    ``date`` values serialize as ISO 8601 via :meth:`datetime.date.isoformat`;
    ``None`` serializes as an empty cell. Rows use ``lineterminator="\\n"``
    for deterministic cross-platform output.

    Args:
        records: The records to serialize.
        output: One of three output modes:

            - ``None``: return the CSV text as a ``str``.
            - A ``str`` or ``os.PathLike``: write UTF-8 CSV to that path
              (using ``newline=""`` as required by the :mod:`csv` docs) and
              return ``None``.
            - A file-like object (``TextIO``): write to it directly and
              return ``None``. The caller's object is not closed.

    Returns:
        The CSV text when ``output`` is ``None``, otherwise ``None``.
    """
    rows = [_flatten(record) for record in records]

    if output is None:
        buffer = io.StringIO()
        _write_csv(buffer, rows)
        return buffer.getvalue()

    if isinstance(output, (str, os.PathLike)):
        with open(Path(output), "w", encoding="utf-8", newline="") as stream:
            _write_csv(stream, rows)
    else:
        _write_csv(output, rows)
    return None


def _write_csv(stream: TextIO, rows: list[list[str]]) -> None:
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(CSV_COLUMNS)
    writer.writerows(rows)


def _flatten(record: EOXRecord) -> list[str]:
    details = record.migration_details
    return [
        _cell(record.eol_product_id),
        _cell(record.product_id_description),
        _cell(record.product_bulletin_number),
        _cell(record.link_to_product_bulletin_url),
        _cell(record.eox_external_announcement_date),
        _cell(record.end_of_sale_date),
        _cell(record.end_of_sw_maintenance_releases),
        _cell(record.end_of_security_vul_support_date),
        _cell(record.end_of_routine_failure_analysis_date),
        _cell(record.end_of_service_contract_renewal),
        _cell(record.last_date_of_support),
        _cell(record.end_of_svc_attach_date),
        _cell(record.updated_time_stamp),
        _cell(record.eox_input_type),
        _cell(record.eox_input_value),
        _cell(details.pid_active_flag if details else None),
        _cell(details.migration_information if details else None),
        _cell(details.migration_option if details else None),
        _cell(details.migration_product_id if details else None),
        _cell(details.migration_product_name if details else None),
        _cell(details.migration_strategy if details else None),
        _cell(details.migration_product_info_url if details else None),
    ]


def _cell(value: str | date | None) -> str:
    if value is None:
        return ""
    if isinstance(value, date):
        return value.isoformat()
    return value
