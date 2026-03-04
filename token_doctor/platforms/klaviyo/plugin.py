"""
Klaviyo plugin: token check via /api/lists or /api/metrics (API key).

Revision 2024-04-15 or later; uses Klaviyo-Revison and Authorization: Klaviyo-API-Key.
"""

from __future__ import annotations

from typing import Any

from token_doctor.core.http_client import get
from token_doctor.core.schema import CheckResult, CheckStatus, NormalizedEvent
from token_doctor.platforms.base import safe_fetch_feed

DECLARED_ENDPOINTS = [
    "https://a.klaviyo.com/api/lists",
    "https://a.klaviyo.com/api/metrics",
]
CHANGELOG_FEEDS = [
    "https://developers.klaviyo.com/en/blog/feed",
]
DOCS_LINKS = [
    "https://developers.klaviyo.com/en/reference/api-overview",
    "https://developers.klaviyo.com/en/blog",
]

metadata = {
    "platform": "klaviyo",
    "auth_types": ["api_key", "private_api_key"],
    "documentation_links": DOCS_LINKS,
    "declared_endpoints": DECLARED_ENDPOINTS,
    "sources_monitored": CHANGELOG_FEEDS,
    "data_collected": ["lists or metrics for validation", "developer blog feed"],
}


def token_checks(token: str, config: Any) -> list[CheckResult]:
    """Validate Klaviyo API key via GET /api/lists (Klaviyo-API-Key header)."""
    results: list[CheckResult] = []
    endpoint = "https://a.klaviyo.com/api/lists"
    try:
        resp = get(
            endpoint,
            headers={
                "Authorization": f"Klaviyo-API-Key {token}",
                "revision": "2024-04-15",
            },
            raise_for_status=False,
        )
        if resp.status_code == 200:
            results.append(
                CheckResult(
                    name="validity",
                    status=CheckStatus.OK,
                    message="Token valid",
                    details={},
                    endpoint_used=endpoint,
                )
            )
        elif resp.status_code in (401, 403):
            results.append(
                CheckResult(
                    name="validity",
                    status=CheckStatus.ERROR,
                    message="Token invalid or expired",
                    endpoint_used=endpoint,
                )
            )
        else:
            results.append(
                CheckResult(
                    name="validity",
                    status=CheckStatus.WARNING,
                    message=f"Unexpected status {resp.status_code}",
                    details={"status_code": resp.status_code},
                    endpoint_used=endpoint,
                )
            )
    except Exception as e:
        results.append(
            CheckResult(
                name="validity",
                status=CheckStatus.ERROR,
                message=str(e)[:200],
                endpoint_used=endpoint,
            )
        )
    return results


def collect_changes(since: Any) -> list[NormalizedEvent]:
    events: list[NormalizedEvent] = []
    for url in CHANGELOG_FEEDS:
        events.extend(safe_fetch_feed(url, "klaviyo", since=since))
    return events


def collect_status() -> None:
    return None


plugin = type("KlaviyoPlugin", (), {
    "metadata": metadata,
    "token_checks": lambda self, token, config: token_checks(token, config),
    "collect_changes": lambda self, since: collect_changes(since),
    "collect_status": lambda self: collect_status(),
})()
