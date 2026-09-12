# cisco-eox-query

Python client for the [Cisco End-of-Life (EOX) API](https://developer.cisco.com/docs/support-apis/eox).

Built on `httpx` for transport and `pydantic` for response models. This package
implements the Cisco EOX API v5 as described by
`Cisco-End-of-Life-EOX-v5_0.wadl`.

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

If you already hold a token:

```python
client = EOXClient(access_token="...")
```

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

## Development

```bash
uv sync
uv run pytest
uv build
```