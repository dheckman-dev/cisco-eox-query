from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

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


def test_retry_after_http_date_honored(monkeypatch):
    calls = []
    sleeps = []
    monkeypatch.setattr("cisco_eox_query._base.time.sleep", sleeps.append)
    retry_at = datetime.now(timezone.utc) + timedelta(seconds=10)
    retry_after = format_datetime(retry_at, usegmt=True)

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(429, headers={"Retry-After": retry_after})
        return httpx.Response(200, json=_payload())

    client = _client(handler)
    response = client.search_by_product_ids("WIC-1T=")
    assert len(calls) == 2
    assert len(sleeps) == 1
    assert 8.0 <= sleeps[0] <= 10.5


def test_retry_after_seconds_honored(monkeypatch):
    calls = []
    sleeps = []
    monkeypatch.setattr("cisco_eox_query._base.time.sleep", sleeps.append)

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(429, headers={"Retry-After": "3"})
        return httpx.Response(200, json=_payload())

    client = _client(handler)
    response = client.search_by_product_ids("WIC-1T=")
    assert len(calls) == 2
    assert sleeps == [3.0]


def test_retry_after_invalid_falls_back_to_retry_delay(monkeypatch):
    calls = []
    sleeps = []
    monkeypatch.setattr("cisco_eox_query._base.time.sleep", sleeps.append)

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(429, headers={"Retry-After": "not-a-date"})
        return httpx.Response(200, json=_payload())

    client = _client(handler, retry_delay=2.0)
    response = client.search_by_product_ids("WIC-1T=")
    assert len(calls) == 2
    assert sleeps == [2.0]


def test_retry_after_negative_clamped_to_zero(monkeypatch):
    calls = []
    sleeps = []
    monkeypatch.setattr("cisco_eox_query._base.time.sleep", sleeps.append)

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(429, headers={"Retry-After": "-5"})
        return httpx.Response(200, json=_payload())

    client = _client(handler)
    response = client.search_by_product_ids("WIC-1T=")
    assert len(calls) == 2
    assert sleeps == [0.0]


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


def test_throttle_spaces_requests(monkeypatch):
    sleeps = []
    monkeypatch.setattr("cisco_eox_query._base.time.sleep", sleeps.append)
    monkeypatch.setattr("cisco_eox_query._base.time.monotonic", lambda: 0.0)
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=_payload())

    client = _client(handler, min_request_interval=0.2)
    client.search_by_product_ids("A")
    client.search_by_product_ids("B")
    assert sleeps == [0.2]
    assert len(calls) == 2


def test_close_closes_http_client():
    client = _client(lambda request: httpx.Response(200, json=_payload()))
    assert not client._client.is_closed
    client.close()
    assert client._client.is_closed


def test_context_manager_closes_client():
    with _client(lambda request: httpx.Response(200, json=_payload())) as client:
        assert not client._client.is_closed
    assert client._client.is_closed


def test_missing_credentials_rejected():
    with pytest.raises(ValueError):
        EOXClient()


def test_negative_max_retries_rejected():
    with pytest.raises(ValueError):
        EOXClient(
            access_token="dummy",
            max_retries=-1,
            transport=httpx.MockTransport(lambda request: httpx.Response(200)),
        )


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


def test_token_post_body_contains_client_credentials():
    calls = []

    def handler(request):
        calls.append(request)
        if request.method == "POST":
            return _token_response("tok")
        return httpx.Response(200, json=_payload())

    client = _credential_client(handler)
    client.search_by_product_ids("WIC-1T=")
    body = [r.content.decode() for r in calls if r.method == "POST"][0]
    assert "grant_type=client_credentials" in body
    assert "client_id=cid" in body
    assert "client_secret=csecret" in body


def test_retry_get_requests_always_authorized(monkeypatch):
    calls = []
    sleeps = []
    monkeypatch.setattr("cisco_eox_query._base.time.sleep", sleeps.append)

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(200, json=_payload())

    client = _client(handler)
    client.search_by_product_ids("WIC-1T=")
    get_requests = [r for r in calls if r.method == "GET"]
    assert len(get_requests) == 2
    assert all(r.headers["authorization"] == "Bearer dummy" for r in get_requests)


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