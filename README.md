# cisco-eox-query

Python client for the [Cisco End-of-Life (EOX) API](https://developer.cisco.com/docs/support-apis/eox).

Built on `httpx` for transport and `pydantic` for response models. This package
implements the Cisco EOX API v5 as described by
`Cisco-End-of-Life-EOX-v5_0.wadl`.

![Python versions](https://img.shields.io/pypi/pyversions/cisco-eox-query?cacheSeconds=86400)
![Coverage](https://img.shields.io/codecov/c/github/dheckman-dev/cisco-eox-query)

## Versioning

Library major versions track the EOX API version:

| `cisco-eox-query` | EOX API | Status |
| --- | --- | --- |
| 1.x | v5 | current |
| 2.x | v6 | future, when released |

The versioned implementation lives under `cisco_eox_query.v5`. The top-level
package re-exports the latest supported version for convenience.

## Install

```bash
pip install cisco-eox-query
```

## Authentication

EOX is one of the Cisco Support APIs and requires a Smart Net Total Care (SNTC)
or Partner Support Service (PSS) entitlement. Register an application at the
[Cisco API Console](https://apiconsole.cisco.com/) to obtain a client ID and
client secret. The client exchanges them for a bearer token (client-credentials
grant) and refreshes it automatically before expiry.

## Usage

```python
from cisco_eox_query import EOXClient

with EOXClient(client_id="...", client_secret="...") as client:
    records = list(client.iter_product_ids(["WS-C2960X-48TS-L", "WIC-1T="]))
    for record in records:
        print(record.eol_product_id, record.last_date_of_support)
```

All four WADL endpoints are exposed as `search_*` methods returning an
`EOXResponse` (with `records`, `pagination`, and optional `error`), plus
`iter_*` variants that follow pagination automatically:

| Endpoint | Method |
| --- | --- |
| `EOXByDates/{pageIndex}/{startDate}/{endDate}` | `search_by_dates` / `iter_dates` |
| `EOXByProductID/{pageIndex}/{productIDs}` | `search_by_product_ids` / `iter_product_ids` |
| `EOXBySerialNumber/{pageIndex}/{serialNumbers}` | `search_by_serial_numbers` / `iter_serial_numbers` |
| `EOXBySWReleaseString/{pageIndex}` | `search_by_software_releases` / `iter_software_releases` |

The `iter_*` variants accept an optional `max_pages` keyword (default 1000) as
a safety valve against runaway pagination; if the API never reports a final
page, a `PaginationError` is raised instead of looping forever.

If you already hold a token:

```python
client = EOXClient(access_token="...")
```

### CSV export

Records from any `search_*` or `iter_*` call can be serialized to CSV with
`export_to_csv`. The header row is always written, even for an empty result
set. Columns follow the flattened schema: the 15 top-level `EOXRecord` fields
plus seven `Migration*` columns from `migration_details`. The `QueryType`
column holds the normalized query type (one of `product_id`,
`serial`, `software`, `dates`) rather than the raw API
echo. `date` values are written in ISO-8601 format; `None` becomes an empty
cell.

```python
from cisco_eox_query import EOXClient, export_to_csv

with EOXClient(client_id="...", client_secret="...") as client:
    records = list(client.iter_product_ids(["WS-C2960X-48TS-L"]))
    csv_text = export_to_csv(records)  # CSV text as a str
    export_to_csv(records, output="eox.csv")  # write a UTF-8 CSV file
```

With `output=None` (the default) the CSV text is returned. Passing a path
writes a UTF-8 file; passing a file-like object writes to it directly. An
empty `records` list still produces a document with just the header row.

Exported cells contain API data verbatim. Cells beginning with a spreadsheet
formula trigger (`=`, `+`, `-`, `@`) could be interpreted as formulas if the
CSV is opened in Excel, LibreOffice, or Google Sheets, so treat exported CSVs
as untrusted data when opening them in a spreadsheet.

### Excel export

Records can also be serialized to an Excel workbook with `export_to_xlsx`. It
uses the same flattened column schema as `export_to_csv` (the 15 top-level
`EOXRecord` fields plus seven `Migration*` columns) and always writes the
header row, even for an empty result set. Data types are enforced: `date`
fields become real Excel date cells, strings are text cells, and `None`
becomes an empty cell. As a defense against formula injection, string values
starting with `=`, `+`, `-`, or `@` are written as literal text, never as
formulas.

```python
from cisco_eox_query import EOXClient, export_to_xlsx

with EOXClient(client_id="...", client_secret="...") as client:
    records = list(client.iter_product_ids(["WS-C2960X-48TS-L"]))
    xlsx_bytes = export_to_xlsx(records)  # workbook bytes
    export_to_xlsx(records, output="eox.xlsx")  # write an .xlsx file
```

With `output=None` (the default) the workbook bytes are returned. Passing a
path writes an `.xlsx` file; passing a binary file-like object writes to it
directly. An empty `records` list still produces a workbook with just the
header row.

### Query types

`EOXRecord.eox_input_type` is normalized to one of four stable values:

| Normalized | Raw API echo |
| --- | --- |
| `product_id` | `ShowEOXByPids` |
| `serial` | `ShowEOXBySerialNumber` |
| `software` | `ShowEOXBySoftware` |
| `dates` | `showEoXByDates` |

Raw API echo values are matched case-insensitively; unknown values pass
through unchanged. `cisco_eox_query.QUERY_TYPES` exports the set of normalized
values and can be used as a reference for relational DB schema constraints.
The discriminator is useful when merging records from multiple query methods
(e.g. building relational tables keyed by product_id / serial / software).

## Command line

The package installs an `eox-query` console script. Credentials may be passed
as flags or via `EOX_CLIENT_ID`, `EOX_CLIENT_SECRET`, and `EOX_ACCESS_TOKEN`
environment variables.

```bash
eox-query --client-id ... --client-secret ... pid WS-C2960X-48TS-L WIC-1T=
eox-query --client-id ... --client-secret ... serial JAE11108ESH SAD11510738
eox-query --client-id ... --client-secret ... software 12.4\(15\)T,IOS
eox-query --client-id ... --client-secret ... dates 2011-01-01 2015-12-31 --attribs EO_SALES_DATE
```

Results can be exported as CSV or Excel with `--export csv|xlsx`. Without
`--output-file` the CSV is written to stdout; with `--output-file PATH` it is
written to the given file instead. `--output-file` requires `--export csv` or
`--export xlsx`, and `--export xlsx` requires `--output-file` (binary output
is never written to stdout).

```bash
eox-query --client-id ... --client-secret ... --export csv pid WS-C2960X-48TS-L
eox-query --client-id ... --client-secret ... --export csv --output-file eox.csv pid WS-C2960X-48TS-L
eox-query --client-id ... --client-secret ... --export xlsx --output-file eox.xlsx pid WS-C2960X-48TS-L
```

Run `eox-query --examples` for annotated usage examples, or
`eox-query <command> --examples` (e.g. `eox-query pid --examples`) for
command-specific examples. Examples are also embedded in `--help` output.

Logs go to stderr with the format `YYYY-MM-DD HH:MM:SS - SEVERITY - module - message`; queried records print to stdout so they can be piped. Diagnostics are silent by default and increase with `-v` (info) / `-vv` (debug).

```bash
eox-query -vv --client-id ... --client-secret ... pid WIC-1T=
```

Library users get the same structured loggers (`cisco_eox_query._base`, `cisco_eox_query.v5.client`, ...) without any handler configuration.

## Rate limiting and retries

The EOX API is limited to 5 requests/second and 5000 requests/day. The client
handles this automatically:

- Requests are throttled to stay under the per-second limit (default 0.25s
  between requests, configurable via `min_request_interval`).
- HTTP 429/408/425/5xx responses and transport errors are retried up to
  `max_retries` times (default 3) with `retry_delay` seconds between attempts
  (default 5s), honoring the server's `Retry-After` header (both delay-seconds
  and RFC 7231 HTTP-date formats) when present.
- After retries are exhausted on a 429, a `RateLimitError` is raised; the CLI
  prints a message about hitting the daily limit and exits with code 2.
- Non-retryable errors (e.g. HTTP 403) are raised immediately.

```python
from cisco_eox_query import EOXClient, RateLimitError

with EOXClient(client_id="...", client_secret="...", max_retries=5, retry_delay=2.0) as client:
    try:
        for record in client.iter_product_ids(["WIC-1T="]):
            print(record.eol_product_id)
    except RateLimitError as exc:
        print(f"Hit the daily request limit: {exc}")
```

## Error handling

- `EOXAPIError` — raised when a response contains an `EOXError` payload. Call
  `response.raise_for_error()` on `search_*` results; the `iter_*` variants
  raise automatically.
- `RetryError` — a request failed after exhausting all retries.
- `RateLimitError` — a rate-limited request failed after exhausting retries
  (subclass of `RetryError`).
- `PaginationError` — pagination did not terminate within `max_pages`
  (subclass of `RetryError`).
- `ValueError` — invalid input, a malformed JSON response body, or an
  unexpected response shape (possible API schema change). The message includes
  the request path and the first validation error.

The client tolerates common API quirks: a `null` `EOXRecord` is treated as an
empty result set, and a single record returned as a bare object (not wrapped
in a list) is accepted.

## Development

```bash
uv sync
uv run pytest
uv build
```