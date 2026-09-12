from __future__ import annotations

import time

import httpx
import pytest

from cisco_eox_query import RateLimitError, RetryError
from cisco_eox_query.v5.client import EOXClient


def _client(handler, **kwargs) -> EOXClient:
    kwargs.setdefault("retry_delay", 0.0)
    kwargs.setdefault("min_request_interval", 0.0)
    return EOXClient(access_token="dummy", transport=httpx.MockTransport(handler), **kwargs)


def _credential_client(handler, **kwargs) -> EOXClient:
    kwargs.setdefault("retry_delay", 0.0)
    kwargs.setdefault("min_request_interval", 0.0)
    return EOXClient(
        client_id="cid",
        client_secret="csecret",
        transport=httpx.MockTransport(handler),
        **kwargs,
    )


def _token_response(token: str) -> httpx.Response:
    return httpx.Response(200, json={"access_token": token, "expires_in": 3600})


def _payload() -> dict:
    return {"EOXRecord": [], "PaginationResponseRecord": {}}


def test_retries_on_429_then_succeeds():
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) <= 2:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(200, json=_payload())

    client = _client(handler)
    response = client.search_by_product_ids("WIC-1T=")
    assert len(calls) == 3
    assert response.records == []


def test_retries_exhausted_on_429_raises_rate_limit():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(429)

    client = _client(handler, max_retries=2)
    with pytest.raises(RateLimitError) as exc_info:
        client.search_by_product_ids("WIC-1T=")
    assert "5000" in str(exc_info.value)
    assert len(calls) == 3


def test_retries_on_503_then_succeeds():
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(503)
        return httpx.Response(200, json=_payload())

    client = _client(handler)
    client.search_by_serial_numbers("FHK0933224R")
    assert len(calls) == 2


def test_retries_exhausted_on_503_raises_retry_error():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(503)

    client = _client(handler, max_retries=1)
    with pytest.raises(RetryError):
        client.search_by_product_ids("WIC-1T=")
    assert len(calls) == 2


def test_transport_error_retries_then_succeeds():
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            raise httpx.ConnectError("connection refused")
        return httpx.Response(200, json=_payload())

    client = _client(handler)
    client.search_by_dates("2011-01-01", "2011-01-31")
    assert len(calls) == 2


def test_transport_error_exhausted_raises_retry_error():
    calls = []

    def handler(request):
        calls.append(request)
        raise httpx.ConnectError("connection refused")

    client = _client(handler, max_retries=1)
    with pytest.raises(RetryError):
        client.search_by_product_ids("WIC-1T=")
    assert len(calls) == 2


def test_non_retryable_4xx_not_retried():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(403)

    client = _client(handler)
    with pytest.raises(httpx.HTTPStatusError):
        client.search_by_product_ids("WIC-1T=")
    assert len(calls) == 1


def test_throttle_spaces_requests():
    started = time.monotonic()
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=_payload())

    client = _client(handler, min_request_interval=0.2)
    client.search_by_product_ids("A")
    client.search_by_product_ids("B")
    assert time.monotonic() - started >= 0.15


def test_malformed_json_body_raises_value_error():
    def handler(request):
        return httpx.Response(200, text="<html>502 Bad Gateway</html>")

    client = _client(handler)
    with pytest.raises(ValueError) as exc_info:
        client.search_by_product_ids("WIC-1T=")
    assert "invalid JSON response" in str(exc_info.value)
    assert "HTTP 200" in str(exc_info.value)


def test_empty_body_raises_value_error():
    def handler(request):
        return httpx.Response(200)

    client = _client(handler)
    with pytest.raises(ValueError) as exc_info:
        client.search_by_product_ids("WIC-1T=")
    assert "invalid JSON response" in str(exc_info.value)
    assert "HTTP 200" in str(exc_info.value)


def test_token_refreshes_when_expired():
    calls = []

    def handler(request):
        calls.append(request)
        if request.method == "POST":
            return _token_response("tok")
        return httpx.Response(200, json=_payload())

    client = _credential_client(handler)
    assert len(calls) == 1
    client._token_expiry = time.monotonic() - 1
    response = client.search_by_product_ids("WIC-1T=")
    assert response.records == []
    assert sum(r.method == "POST" for r in calls) == 2
    assert sum(r.method == "GET" for r in calls) == 1


def test_401_with_credentials_refreshes_and_retries():
    calls = []
    tokens = ["tok1", "tok2"]

    def handler(request):
        calls.append(request)
        if request.method == "POST":
            return _token_response(tokens.pop(0))
        if request.headers.get("authorization") == "Bearer tok1":
            return httpx.Response(401)
        return httpx.Response(200, json=_payload())

    client = _credential_client(handler)
    response = client.search_by_product_ids("WIC-1T=")
    assert response.records == []
    assert sum(r.method == "POST" for r in calls) == 2
    assert sum(r.method == "GET" for r in calls) == 2
    assert [r.headers["authorization"] for r in calls if r.method == "GET"] == [
        "Bearer tok1",
        "Bearer tok2",
    ]


def test_401_with_access_token_only_raises():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(401)

    client = _client(handler)
    with pytest.raises(httpx.HTTPStatusError):
        client.search_by_product_ids("WIC-1T=")
    assert sum(r.method == "GET" for r in calls) == 1
    assert sum(r.method == "POST" for r in calls) == 0


def test_401_after_refresh_still_raises():
    calls = []

    def handler(request):
        calls.append(request)
        if request.method == "POST":
            return _token_response("tok")
        return httpx.Response(401)

    client = _credential_client(handler)
    with pytest.raises(httpx.HTTPStatusError):
        client.search_by_product_ids("WIC-1T=")
    assert sum(r.method == "POST" for r in calls) == 2
    assert sum(r.method == "GET" for r in calls) == 2


def test_token_response_missing_access_token_raises():
    def handler(request):
        return httpx.Response(200, json={"expires_in": 3600})

    with pytest.raises(ValueError) as exc_info:
        _credential_client(handler)
    assert "no access_token" in str(exc_info.value)


def test_token_response_invalid_json_raises():
    def handler(request):
        return httpx.Response(200, text="<html>oops</html>")

    with pytest.raises(ValueError) as exc_info:
        _credential_client(handler)
    assert "invalid JSON from token endpoint" in str(exc_info.value)