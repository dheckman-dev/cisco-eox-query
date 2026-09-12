from __future__ import annotations

import httpx
import pytest

from cisco_eox_query.constants import BASE_URL, TOKEN_URL
from cisco_eox_query.v5.client import EOXClient
from cisco_eox_query.v5.models import EOXAPIError


def _client(handler) -> EOXClient:
    return EOXClient(access_token="dummy", transport=httpx.MockTransport(handler))


def _json_response(payload: dict | None = None) -> httpx.Response:
    return httpx.Response(200, json=payload or {"EOXRecord": [], "PaginationResponseRecord": {}})


def test_token_flow_uses_client_credentials():
    calls = []

    def handler(request):
        calls.append(request)
        if request.method == "POST":
            assert str(request.url) == TOKEN_URL
            return httpx.Response(200, json={"access_token": "tok", "expires_in": 3600})
        return _json_response()

    client = EOXClient(client_id="cid", client_secret="csecret", transport=httpx.MockTransport(handler))
    client.search_by_product_ids("WIC-1T=")
    assert any(r.method == "POST" for r in calls)
    assert [r.headers["authorization"] for r in calls if r.method == "GET"] == ["Bearer tok"]


def test_search_by_product_ids_path():
    captured = {}

    def handler(request):
        captured["url"] = str(request.url)
        return _json_response()

    client = _client(handler)
    client.search_by_product_ids(["15216-OADM1-35=", "M92S1K9-1.3.3C"])
    assert captured["url"].startswith(BASE_URL)
    assert "/supporttools/eox/rest/5/EOXByProductID/1/15216-OADM1-35=,M92S1K9-1.3.3C" in captured["url"]


def test_search_by_serial_numbers_page():
    captured = {}

    def handler(request):
        captured["url"] = str(request.url)
        return _json_response()

    client = _client(handler)
    client.search_by_serial_numbers(["JAE11108ESH", "SAD11510738"], page=3)
    assert "/EOXBySerialNumber/3/JAE11108ESH,SAD11510738" in captured["url"]


def test_search_by_software_releases_inputs():
    captured = {}

    def handler(request):
        captured["url"] = str(request.url)
        return _json_response()

    client = _client(handler)
    client.search_by_software_releases(("12.4(15)T", "IOS"), ("9.21(7)", "NX-OS"))
    assert "/EOXBySWReleaseString/1" in captured["url"]
    assert "input1=12.4%2815%29T%2CIOS" in captured["url"]
    assert "input2=9.21%287%29%2CNX-OS" in captured["url"]


def test_search_by_dates_attribs():
    captured = {}

    def handler(request):
        captured["url"] = str(request.url)
        return _json_response()

    client = _client(handler)
    client.search_by_dates("2011-01-01", "2015-12-31", attribs=["EO_SALES_DATE", "EO_LAST_SUPPORT_DATE"])
    assert "/EOXByDates/1/2011-01-01/2015-12-31" in captured["url"]
    assert "eoxAttrib=EO_SALES_DATE%2CEO_LAST_SUPPORT_DATE" in captured["url"]


def test_iter_dates_paginates():
    pages = {
        "1": {
            "PaginationResponseRecord": {"PageIndex": 1, "LastIndex": 2, "TotalRecords": 2, "PageRecords": 1},
            "EOXRecord": [{"EOLProductID": "P1"}],
        },
        "2": {
            "PaginationResponseRecord": {"PageIndex": 2, "LastIndex": 2, "TotalRecords": 2, "PageRecords": 1},
            "EOXRecord": [{"EOLProductID": "P2"}],
        },
    }

    def handler(request):
        page = request.url.path.split("/EOXByDates/")[1].split("/")[0]
        return httpx.Response(200, json=pages[page])

    client = _client(handler)
    assert [r.eol_product_id for r in client.iter_dates("2011-01-01", "2011-01-31")] == ["P1", "P2"]


def test_invalid_attrib_rejected():
    client = _client(lambda request: _json_response())
    with pytest.raises(ValueError):
        client.search_by_dates("2011-01-01", "2011-01-31", attribs=["BOGUS"])


def test_error_response_raises():
    payload = {"EOXError": {"ErrorID": "SSA_ERR_034", "ErrorDescription": "Access denied."}}

    def handler(request):
        return httpx.Response(200, json=payload)

    client = _client(handler)
    with pytest.raises(EOXAPIError):
        client.search_by_product_ids("WIC-1T=").raise_for_error()


def test_too_many_inputs_rejected():
    client = _client(lambda request: _json_response())
    with pytest.raises(ValueError):
        client.search_by_product_ids([f"PID{i}" for i in range(21)])