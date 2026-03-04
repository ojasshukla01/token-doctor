"""
HTTP client wrapper with retries, rate limiting, and safe logging.

- All API-related exceptions are mapped to token_doctor exceptions.
- Tokens are never logged or included in error messages.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from token_doctor.core.exceptions import (
    APIError,
    AuthenticationError,
    NetworkError,
    RateLimitError,
)
from token_doctor.core.redaction import redact_string

USER_AGENT = "token-doctor/0.1.0 (local; no remote server)"

# Default timeouts and retries
DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_RETRIES = 2
DEFAULT_RATE_LIMIT_DELAY = 0.5


def safe_log_response(response: httpx.Response) -> str:
    """Return a redacted representation of response for logging (no tokens)."""
    text = (response.text or "")[:500]
    return redact_string(f"status={response.status_code} body_preview={text}")


def get_client(
    timeout: float = DEFAULT_TIMEOUT,
    headers: dict[str, str] | None = None,
) -> httpx.Client:
    """Build httpx client with safe defaults."""
    merged = dict(headers or {})
    merged.setdefault("User-Agent", USER_AGENT)
    return httpx.Client(
        timeout=timeout,
        headers=merged,
        follow_redirects=True,
    )


def _raise_for_response(response: httpx.Response, url: str) -> None:
    """
    Raise appropriate token_doctor exception for 4xx/5xx.
    Response body is redacted before attaching.
    """
    status = response.status_code
    body = (response.text or "")[:1000]
    redacted_body = redact_string(body)
    details: dict[str, Any] = {"url": url, "status_code": status}
    if status == 429:
        retry_after = response.headers.get("Retry-After")
        raise RateLimitError(
            "API rate limit exceeded. Try again later or with --offline.",
            {**details, "retry_after": retry_after, "response_preview": redacted_body},
            status_code=status,
            response_body=redacted_body,
        )
    if status in (401, 403):
        raise AuthenticationError(
            "Token invalid, expired, or insufficient permissions.",
            {**details, "response_preview": redacted_body},
            status_code=status,
            response_body=redacted_body,
        )
    if 400 <= status < 500:
        raise APIError(
            f"Client error from API (HTTP {status}).",
            {**details, "response_preview": redacted_body},
            status_code=status,
            response_body=redacted_body,
        )
    if status >= 500:
        raise APIError(
            f"Server error from API (HTTP {status}). Retry later.",
            {**details, "response_preview": redacted_body},
            status_code=status,
            response_body=redacted_body,
        )


def get(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    token: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    rate_limit_delay: float = DEFAULT_RATE_LIMIT_DELAY,
    raise_for_status: bool = False,
) -> httpx.Response:
    """
    Perform GET with optional Bearer auth and retries.
    Never logs or echoes the token.
    Raises NetworkError, RateLimitError, AuthenticationError, APIError on failure.
    """
    merged = dict(headers or {})
    if token:
        merged["Authorization"] = f"Bearer {token}"
    merged.setdefault("User-Agent", USER_AGENT)
    last_exc: Exception | None = None
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        for attempt in range(max_retries + 1):
            try:
                if rate_limit_delay and attempt > 0:
                    time.sleep(rate_limit_delay)
                response = client.get(url, headers=merged)
                if raise_for_status and response.status_code >= 400:
                    _raise_for_response(response, url)
                return response
            except (RateLimitError, AuthenticationError):
                raise
            except httpx.TimeoutException:
                last_exc = NetworkError(
                    "Request timed out. Check connectivity or use --offline.",
                    {"url": url},
                    timeout=True,
                )
            except httpx.ConnectError:
                last_exc = NetworkError(
                    "Connection failed. Check URL and network or use --offline.",
                    {"url": url},
                    connection_failed=True,
                )
            except httpx.HTTPError as e:
                last_exc = NetworkError(
                    redact_string(str(e)),
                    {"url": url},
                )
        if last_exc:
            raise last_exc
        raise RuntimeError("Unexpected get() state")


def post(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    token: str | None = None,
    json: dict[str, Any] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    raise_for_status: bool = False,
) -> httpx.Response:
    """
    Perform POST with optional Bearer auth. Never logs token.
    Raises same exceptions as get().
    """
    merged = dict(headers or {})
    if token:
        merged["Authorization"] = f"Bearer {token}"
    merged.setdefault("User-Agent", USER_AGENT)
    last_exc: Exception | None = None
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        for _ in range(max_retries + 1):
            try:
                response = client.post(url, headers=merged, json=json or {})
                if raise_for_status and response.status_code >= 400:
                    _raise_for_response(response, url)
                return response
            except (RateLimitError, AuthenticationError):
                raise
            except httpx.TimeoutException:
                last_exc = NetworkError(
                    "Request timed out.",
                    {"url": url},
                    timeout=True,
                )
            except httpx.ConnectError:
                last_exc = NetworkError(
                    "Connection failed.",
                    {"url": url},
                    connection_failed=True,
                )
            except httpx.HTTPError as e:
                last_exc = NetworkError(redact_string(str(e)), {"url": url})
        if last_exc:
            raise last_exc
        raise RuntimeError("Unexpected post() state")


def check_rate_limit(response: httpx.Response) -> bool:
    """Return True if response indicates rate limit (429 or Retry-After)."""
    if response.status_code == 429:
        return True
    ra = response.headers.get("Retry-After")
    return bool(ra and str(ra).isdigit())
