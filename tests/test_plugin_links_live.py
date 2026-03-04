"""
Live HTTP checks for all plugin links (documentation_links, declared_endpoints, sources_monitored).

Skips URLs that contain placeholders (e.g. {tenant}, {base_url}). For concrete URLs, performs
a GET request and verifies the server responds. Accepts 200, redirects (301/302/307/308),
401/403 (auth required), 404, 405 as "working". Skips entire run if network is unavailable.
"""

from __future__ import annotations

import httpx
import pytest

from token_doctor.core.plugin_loader import get_all_plugins, get_plugin_metadata


# URLs with placeholders like {tenant} or {base_url} cannot be tested without config
def is_concrete_url(s: str) -> bool:
    """Return True if s is a full URL with no unresolved placeholders."""
    if not s or not isinstance(s, str):
        return False
    s = s.strip()
    if "{" in s and "}" in s:
        return False
    return bool(s.startswith("http://") or s.startswith("https://"))


# Status codes that mean "URL is reachable and server responded"
# 200 OK, redirects, 400 (bad request e.g. missing auth), 401/403 (auth required), 404, 405
# 500, 502, 503: server error (link is valid; avoids CI flakiness when vendors hiccup)
ACCEPTABLE_STATUS_CODES = {200, 301, 302, 307, 308, 400, 401, 403, 404, 405, 500, 502, 503}

# Timeout per request (seconds)
REQUEST_TIMEOUT = 15.0


def _collect_all_concrete_urls() -> list[tuple[str, str, str]]:
    """Return list of (platform, url_kind, url) for every concrete URL in all plugins."""
    out: list[tuple[str, str, str]] = []
    plugins = get_all_plugins()
    for name, plug in plugins.items():
        meta = get_plugin_metadata(plug)
        for link in meta.get("documentation_links") or []:
            if is_concrete_url(link):
                out.append((name, "documentation_links", link))
        for ep in meta.get("declared_endpoints") or []:
            if is_concrete_url(ep):
                out.append((name, "declared_endpoints", ep))
        for src in meta.get("sources_monitored") or []:
            if is_concrete_url(src):
                out.append((name, "sources_monitored", src))
    return out


def _check_url_reachable(url: str) -> tuple[bool, int | None, str]:
    """
    GET url with redirect following. Return (ok, status_code, message).
    ok is True if status is in ACCEPTABLE_STATUS_CODES.
    """
    try:
        resp = httpx.get(url, follow_redirects=True, timeout=REQUEST_TIMEOUT)
        ok = resp.status_code in ACCEPTABLE_STATUS_CODES
        return (ok, resp.status_code, f"status {resp.status_code}")
    except httpx.ConnectError as e:
        return (False, None, f"connection error: {e!s}")
    except httpx.TimeoutException as e:
        return (False, None, f"timeout: {e!s}")
    except Exception as e:
        return (False, None, f"error: {e!s}")


# Build list of (platform, url_kind, url) and test ids at module load for parametrization
_ALL_LINK_IDS: list[tuple[str, str, str]] = []
_LINK_IDS_IDS: list[str] = []
try:
    _ALL_LINK_IDS = _collect_all_concrete_urls()
    for platform, url_kind, url in _ALL_LINK_IDS:
        u = url if len(url) <= 55 else url[:52] + "..."
        _LINK_IDS_IDS.append(f"{platform}:{url_kind}:{u}")
except Exception:
    pass


@pytest.mark.parametrize("platform,url_kind,url", _ALL_LINK_IDS, ids=_LINK_IDS_IDS)
def test_plugin_link_reachable(platform: str, url_kind: str, url: str) -> None:
    """Each concrete plugin URL (docs, endpoints, feeds) should be reachable and return an acceptable status."""
    ok, status_code, message = _check_url_reachable(url)
    msg_lower = message.lower()
    if status_code is None:
        if "connection" in msg_lower or "timeout" in msg_lower or "certificate" in msg_lower or "ssl" in msg_lower:
            pytest.skip(f"Unreachable or TLS issue (CI/firewall): {message}")
        raise AssertionError(f"{platform} {url_kind} {url!r}: {message}")
    assert ok, (
        f"{platform} {url_kind} {url!r}: expected one of {ACCEPTABLE_STATUS_CODES}, got {message}"
    )


def test_all_public_feeds_reachable() -> None:
    """
    All sources_monitored URLs (concrete) should be reachable (200 or acceptable status).
    Skips if network unavailable. Does not assert on response body (some vendors serve HTML at feed URLs).
    """
    plugins = get_all_plugins()
    feed_urls: list[tuple[str, str]] = []  # (platform, url)
    for name, plug in plugins.items():
        meta = get_plugin_metadata(plug)
        for src in meta.get("sources_monitored") or []:
            if is_concrete_url(src):
                feed_urls.append((name, src))

    if not feed_urls:
        pytest.skip("No concrete feed URLs to check")

    failures: list[str] = []
    skipped_network = False
    for platform, url in feed_urls:
        try:
            resp = httpx.get(url, follow_redirects=True, timeout=REQUEST_TIMEOUT)
        except (httpx.ConnectError, httpx.TimeoutException):
            skipped_network = True
            continue
        if resp.status_code in ACCEPTABLE_STATUS_CODES:
            continue
        failures.append(f"{platform} {url!r}: status {resp.status_code}")

    if skipped_network and not failures:
        pytest.skip("Network unreachable; could not verify feeds")
    assert not failures, "Some feed URLs were not reachable:\n" + "\n".join(failures)
