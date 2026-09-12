"""Command-line interface for cisco-eox-query.

Installed as the ``eox-query`` console script.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import Sequence

import httpx

from cisco_eox_query import (
    EOXAPIError,
    EOXClient,
    EOXRecord,
    PaginationError,
    RateLimitError,
    RetryError,
    __version__,
)
from cisco_eox_query.constants import DEFAULT_MAX_PAGES

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"

EXIT_RATE_LIMIT = 2

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="eox-query",
        description="Query the Cisco End-of-Life (EOX) API.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--client-id",
        default=os.environ.get("EOX_CLIENT_ID"),
        help="Cisco API console client ID (or EOX_CLIENT_ID)",
    )
    parser.add_argument(
        "--client-secret",
        default=os.environ.get("EOX_CLIENT_SECRET"),
        help="Cisco API console client secret (or EOX_CLIENT_SECRET)",
    )
    parser.add_argument(
        "--access-token",
        default=os.environ.get("EOX_ACCESS_TOKEN"),
        help="pre-obtained bearer token (or EOX_ACCESS_TOKEN)",
    )
    parser.add_argument("--timeout", type=float, default=30.0, help="request timeout in seconds")
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="increase log verbosity (-v info, -vv debug)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    pid = subparsers.add_parser("pid", help="search by product ID(s)")
    pid.add_argument("product_ids", nargs="+", help="one or more PIDs (wildcards allowed)")

    serial = subparsers.add_parser("serial", help="search by serial number(s)")
    serial.add_argument("serial_numbers", nargs="+", help="one or more serial numbers")

    software = subparsers.add_parser("software", help="search by software release string(s)")
    software.add_argument("releases", nargs="+", help="SWversion[,OSType] tuples, e.g. 12.4(15)T,IOS")

    dates = subparsers.add_parser("dates", help="search by date range")
    dates.add_argument("start", help="start date YYYY-MM-DD")
    dates.add_argument("end", help="end date YYYY-MM-DD")
    dates.add_argument("--attribs", help="comma-separated eoxAttrib values")

    return parser


def setup_logging(level: int = logging.WARNING) -> None:
    logging.basicConfig(level=level, format=LOG_FORMAT, datefmt=LOG_DATEFMT)


def _log_level(verbose: int) -> int:
    if verbose >= 2:
        return logging.DEBUG
    if verbose == 1:
        return logging.INFO
    return logging.WARNING


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    setup_logging(_log_level(args.verbose))
    try:
        with _build_client(args) as client:
            records = _dispatch(client, args)
        for record in records:
            _print_record(record)
        if records:
            logger.info("found %d EOX record(s)", len(records))
        else:
            logger.warning("No EOX records found.")
    except RateLimitError as exc:
        logger.error("%s", exc)
        return EXIT_RATE_LIMIT
    except (ValueError, httpx.HTTPError, EOXAPIError, RetryError) as exc:
        logger.error("%s", exc)
        return 1
    return 0


def _build_client(args: argparse.Namespace) -> EOXClient:
    if args.access_token:
        return EOXClient(access_token=args.access_token, timeout=args.timeout)
    if args.client_id and args.client_secret:
        return EOXClient(client_id=args.client_id, client_secret=args.client_secret, timeout=args.timeout)
    raise ValueError(
        "credentials required: --client-id and --client-secret "
        "(or EOX_CLIENT_ID/EOX_CLIENT_SECRET), or --access-token"
    )


def _dispatch(client: EOXClient, args: argparse.Namespace) -> list[EOXRecord]:
    if args.command == "pid":
        return _collect(client.search_by_product_ids, ",".join(args.product_ids))
    if args.command == "serial":
        return _collect(client.search_by_serial_numbers, ",".join(args.serial_numbers))
    if args.command == "software":
        return _collect(client.search_by_software_releases, *args.releases)
    if args.command == "dates":
        attribs = args.attribs.split(",") if args.attribs else None
        return _collect(client.search_by_dates, args.start, args.end, attribs=attribs)
    raise AssertionError(f"unhandled command: {args.command}")


def _collect(request_fn, *args, **kwargs) -> list[EOXRecord]:
    records = []
    page = 1
    while True:
        if page > DEFAULT_MAX_PAGES:
            raise PaginationError(
                f"pagination did not terminate after {DEFAULT_MAX_PAGES} pages"
            )
        response = request_fn(*args, page=page, **kwargs)
        response.raise_for_error()
        records.extend(response.records)
        last = response.pagination.last_index if response.pagination and response.pagination.last_index else 1
        if page >= last:
            return records
        page += 1


def _print_record(record: EOXRecord) -> None:
    migration = record.migration_details
    print(record.eol_product_id or "<no product id>")
    for label, value in [
        ("Product Description", record.product_id_description),
        ("Bulletin", record.product_bulletin_number),
        ("Bulletin Link", record.link_to_product_bulletin_url),
        ("Announcement", record.eox_external_announcement_date),
        ("End Of Sale", record.end_of_sale_date),
        ("SW Maintenance Ends", record.end_of_sw_maintenance_releases),
        ("Security Vulnerability Support Ends", record.end_of_security_vul_support_date),
        ("Routine Failure Analysis Ends", record.end_of_routine_failure_analysis_date),
        ("Service Contract Renewal", record.end_of_service_contract_renewal),
        ("Last Date of Support", record.last_date_of_support),
        ("Service Attach Ends", record.end_of_svc_attach_date),
        ("Migration Product", migration.migration_information if migration else None),
        ("Migration Product Info URL", migration.migration_product_info_url if migration else None),
        ("Migration Product ID", migration.migration_product_id if migration else None),
        ("Migration Strategy", migration.migration_strategy if migration else None),
    ]:
        if value is not None:
            print(f"  {label:<30} {value}")
