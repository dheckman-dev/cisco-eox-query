"""Command-line interface for cisco-eox-query.

Installed as the ``eox-query`` console script.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Sequence

import httpx

from cisco_eox_query import EOXAPIError, EOXClient, EOXRecord, __version__


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


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        with _build_client(args) as client:
            records = _dispatch(client, args)
        for record in records:
            _print_record(record)
        if not records:
            print("No EOX records found.")
    except (ValueError, httpx.HTTPError, EOXAPIError) as exc:
        print(f"error: {exc}", file=sys.stderr)
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
        response = request_fn(*args, page=page, **kwargs)
        response.raise_for_error()
        records.extend(response.records)
        last = response.pagination.last_index if response.pagination else 1
        if page >= last:
            return records
        page += 1


def _print_record(record: EOXRecord) -> None:
    migration = record.migration_details.migration_product_id if record.migration_details else None
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
        ("Migration Product", record.migration_details.migration_information),
        ("Migration Product Info URL", record.migration_details.migration_product_info_url),
        ("Migration Product ID", record.migration_details.migration_product_id),
        ("Migration Strategy", record.migration_details.migration_strategy),
    ]:
        if value is not None:
            print(f"  {label:<30} {value}")
