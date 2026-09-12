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