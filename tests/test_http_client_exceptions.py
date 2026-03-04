"""Tests for HTTP client: exception mapping for API and network errors."""

import pytest
import respx
from httpx import Response

from token_doctor.core.exceptions import (
    APIError,
    AuthenticationError,
    RateLimitError,
)
from token_doctor.core.http_client import get


@respx.mock
def test_get_returns_response_without_raise():
    respx.get("https://example.com/ok").mock(return_value=Response(200, json={"ok": True}))
    r = get("https://example.com/ok", raise_for_status=False)
    assert r.status_code == 200


@respx.mock
def test_get_4xx_does_not_raise_by_default():
    respx.get("https://example.com/bad").mock(return_value=Response(404))
    r = get("https://example.com/bad", raise_for_status=False)
    assert r.status_code == 404


@respx.mock
def test_get_401_raises_when_raise_for_status():
    respx.get("https://api.example.com/user").mock(return_value=Response(401, text="Unauthorized"))
    with pytest.raises(AuthenticationError) as exc_info:
        get("https://api.example.com/user", raise_for_status=True)
    assert exc_info.value.status_code == 401


@respx.mock
def test_get_429_raises_rate_limit():
    respx.get("https://api.example.com/").mock(
        return_value=Response(429, headers={"Retry-After": "60"})
    )
    with pytest.raises(RateLimitError):
        get("https://api.example.com/", raise_for_status=True)


@respx.mock
def test_get_500_raises_api_error():
    respx.get("https://api.example.com/").mock(
        return_value=Response(500, text="Internal Server Error")
    )
    with pytest.raises(APIError) as exc_info:
        get("https://api.example.com/", raise_for_status=True)
    assert exc_info.value.status_code == 500
