"""Validate all plugin metadata URLs and run smoke tests (no uncaught exceptions)."""

from __future__ import annotations

import re
from urllib.parse import urlparse

import pytest
import respx
from httpx import Response

from token_doctor.core.config import TokenDoctorConfig
from token_doctor.core.plugin_loader import get_all_plugins, get_plugin_metadata


def _is_valid_url_or_template(s: str) -> bool:
    """Return True if s is a valid URL or a template like {base_url}/path or https://{tenant}.example.com."""
    if not s or not isinstance(s, str):
        return False
    s = s.strip()
    # Template with placeholder: {something}
    if "{" in s and "}" in s:
        # Allow https?://... or path starting with /
        return s.startswith("http") or s.startswith("/") or "{" in s
    # Full URL
    if s.startswith(("http://", "https://")):
        try:
            parsed = urlparse(s)
            return bool(parsed.netloc or parsed.path)
        except Exception:
            return False
    # Relative path
    return bool(s.startswith("/"))


def test_all_plugin_documentation_links_are_valid_urls():
    """Every documentation_links entry is a valid URL or template."""
    plugins = get_all_plugins()
    for name, plug in plugins.items():
        meta = get_plugin_metadata(plug)
        links = meta.get("documentation_links") or []
        for link in links:
            assert _is_valid_url_or_template(link), (
                f"{name}: invalid documentation_links entry: {link!r}"
            )


def test_all_plugin_declared_endpoints_are_valid_urls():
    """Every declared_endpoints entry is a valid URL or template."""
    plugins = get_all_plugins()
    for name, plug in plugins.items():
        meta = get_plugin_metadata(plug)
        endpoints = meta.get("declared_endpoints") or []
        for ep in endpoints:
            assert _is_valid_url_or_template(ep), (
                f"{name}: invalid declared_endpoints entry: {ep!r}"
            )


def test_all_plugin_sources_monitored_are_valid_urls():
    """Every sources_monitored entry is a valid URL or template."""
    plugins = get_all_plugins()
    for name, plug in plugins.items():
        meta = get_plugin_metadata(plug)
        sources = meta.get("sources_monitored") or []
        for src in sources:
            assert _is_valid_url_or_template(src), (
                f"{name}: invalid sources_monitored entry: {src!r}"
            )


@pytest.fixture
def minimal_config(tmp_path):
    """Minimal config for smoke tests (no real IO to disk required for plugin calls)."""
    return TokenDoctorConfig(config_dir=tmp_path)


# Catch-all URL pattern for respx (matches any http(s) URL)
_ANY_URL = re.compile(r"^https?://")

@respx.mock
def test_every_plugin_token_checks_no_crash(minimal_config):
    """Call token_checks for every plugin with empty token; no uncaught exception. All HTTP mocked 401."""
    respx.get(_ANY_URL).mock(return_value=Response(401, json={"error": "unauthorized"}))
    respx.post(_ANY_URL).mock(return_value=Response(401, json={"error": "unauthorized"}))

    plugins = get_all_plugins()
    for name, plug in plugins.items():
        results = plug.token_checks("", minimal_config)
        assert isinstance(results, list), f"{name}: token_checks must return a list"
        for r in results:
            assert hasattr(r, "status"), f"{name}: CheckResult must have status"
            assert hasattr(r, "name"), f"{name}: CheckResult must have name"


@respx.mock
def test_every_plugin_collect_changes_no_crash(minimal_config):
    """Call collect_changes for every plugin; no uncaught exception. Feeds mocked with empty/minimal RSS."""
    # Mock any GET (feeds and APIs) so no real network
    respx.get(_ANY_URL).mock(
        return_value=Response(
            200,
            content=b'<?xml version="1.0"?><rss><channel><title>X</title></channel></rss>',
            headers={"Content-Type": "application/xml"},
        )
    )
    respx.post(_ANY_URL).mock(return_value=Response(200, json={}))

    plugins = get_all_plugins()
    for name, plug in plugins.items():
        events = plug.collect_changes(since=None)
        assert isinstance(events, list), f"{name}: collect_changes must return a list"


def test_public_feed_reachable():
    """Verify at least one well-known public changelog feed is reachable (proves HTTP/feed stack works)."""
    import httpx
    # GitHub blog changelog - no auth required, stable URL
    url = "https://github.blog/changelog/feed/"
    try:
        resp = httpx.get(url, follow_redirects=True, timeout=15.0)
        assert resp.status_code == 200, f"Expected 200 for {url}, got {resp.status_code}"
        assert b"<rss" in resp.content or b"<feed" in resp.content or b"<?xml" in resp.content, (
            f"Expected RSS/Atom/XML content from {url}"
        )
    except httpx.ConnectError as e:
        pytest.skip(f"Network unreachable (no internet?): {e}")
    except httpx.TimeoutException as e:
        pytest.skip(f"Request timed out: {e}")
