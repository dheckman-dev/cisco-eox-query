"""Example invocations for the eox-query command-line interface.

The examples are surfaced two ways:

- ``--help`` output embeds a compact examples block via the parser epilog.
- ``--examples`` prints a fuller, annotated list and exits.
"""

from __future__ import annotations

from collections.abc import Sequence

Example = tuple[str, str]

ROOT_EXAMPLES: list[Example] = [
    (
        "Query by product ID",
        "eox-query --client-id ID --client-secret SECRET pid WS-C2960X-48TS-L WIC-1T=",
    ),
    (
        "Query by serial number",
        "eox-query --client-id ID --client-secret SECRET serial JAE11108ESH SAD11510738",
    ),
    (
        "Query by software release",
        "eox-query --client-id ID --client-secret SECRET software '12.4(15)T,IOS'",
    ),
    (
        "Query by date range",
        "eox-query --client-id ID --client-secret SECRET dates 2011-01-01 2015-12-31 --attribs EO_SALES_DATE",  # noqa: E501
    ),
    (
        "Use environment variables for credentials",
        "EOX_CLIENT_ID=ID EOX_CLIENT_SECRET=SECRET eox-query pid WS-C2960X-48TS-L",
    ),
    (
        "Export results as CSV",
        "eox-query --client-id ID --client-secret SECRET --export csv pid WS-C2960X-48TS-L",
    ),
    (
        "Export results to a CSV file",
        "eox-query --client-id ID --client-secret SECRET --export csv --output-file eox.csv pid WS-C2960X-48TS-L",  # noqa: E501
    ),
    (
        "Export results to an Excel file",
        "eox-query --client-id ID --client-secret SECRET --export xlsx --output-file eox.xlsx pid WS-C2960X-48TS-L",  # noqa: E501
    ),
]

COMMAND_EXAMPLES: dict[str, list[Example]] = {
    "pid": [
        (
            "Query a single product",
            "eox-query --client-id ID --client-secret SECRET pid WS-C2960X-48TS-L",
        ),
        (
            "Query multiple products",
            "eox-query --client-id ID --client-secret SECRET pid WS-C2960X-48TS-L WIC-1T=",
        ),
        (
            "Use a wildcard",
            "eox-query --client-id ID --client-secret SECRET pid 'WS-C2960X-*'",
        ),
        (
            "Use a pre-obtained access token",
            "eox-query --access-token TOKEN pid WS-C2960X-48TS-L",
        ),
        (
            "Export results as CSV",
            "eox-query --client-id ID --client-secret SECRET --export csv pid WS-C2960X-48TS-L",
        ),
        (
            "Export results to an Excel file",
            "eox-query --client-id ID --client-secret SECRET --export xlsx --output-file eox.xlsx pid WS-C2960X-48TS-L",  # noqa: E501
        ),
    ],
    "serial": [
        (
            "Query a single serial number",
            "eox-query --client-id ID --client-secret SECRET serial JAE11108ESH",
        ),
        (
            "Query multiple serial numbers",
            "eox-query --client-id ID --client-secret SECRET serial JAE11108ESH SAD11510738",
        ),
        (
            "Use a pre-obtained access token",
            "eox-query --access-token TOKEN serial JAE11108ESH",
        ),
    ],
    "software": [
        (
            "Query by release and OS type",
            "eox-query --client-id ID --client-secret SECRET software '12.4(15)T,IOS'",
        ),
        (
            "Query multiple releases",
            "eox-query --client-id ID --client-secret SECRET software '12.4(15)T,IOS' '15.1(2)T,IOS'",  # noqa: E501
        ),
        (
            "Query by release only",
            "eox-query --client-id ID --client-secret SECRET software '12.4(15)T'",
        ),
    ],
    "dates": [
        (
            "Query a date range",
            "eox-query --client-id ID --client-secret SECRET dates 2011-01-01 2015-12-31",
        ),
        (
            "Filter by a single attribute",
            "eox-query --client-id ID --client-secret SECRET dates 2011-01-01 2015-12-31 --attribs EO_SALES_DATE",  # noqa: E501
        ),
        (
            "Filter by multiple attributes",
            "eox-query --client-id ID --client-secret SECRET dates 2011-01-01 2015-12-31 --attribs EO_SALES_DATE,EO_LAST_SUPPORT_DATE",  # noqa: E501
        ),
    ],
}


def format_examples(examples: Sequence[Example], title: str | None = None) -> str:
    """Format example (description, command) pairs for display.

    Each example is rendered as a description line followed by an indented
    command line. An optional ``title`` is rendered as a header.
    """
    lines: list[str] = []
    if title:
        lines.append(title)
        lines.append("=" * len(title))
        lines.append("")
    for description, command in examples:
        lines.append(f"{description}:")
        lines.append(f"  {command}")
        lines.append("")
    return "\n".join(lines).rstrip()


def format_epilog(examples: Sequence[Example]) -> str:
    """Format a compact examples block for an argparse help epilog."""
    lines = ["examples:"]
    for _, command in examples:
        lines.append(f"  {command}")
    return "\n".join(lines)


__all__ = [
    "COMMAND_EXAMPLES",
    "ROOT_EXAMPLES",
    "format_epilog",
    "format_examples",
]
