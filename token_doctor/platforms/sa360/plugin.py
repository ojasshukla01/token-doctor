"""
Search Ads 360 plugin: token check via SA360 API (agencies or advertisers list).

Google Marketing Platform; OAuth 2.0. Declared endpoints and release notes.
"""

from __future__ import annotations

from typing import Any

from token_doctor.core.http_client import get
from token_doctor.core.schema import CheckResult, CheckStatus, NormalizedEvent
from token_doctor.platforms.base import safe_fetch_feed

# Search Ads 360 API
DECLARED_ENDPOINTS = [
    "https://searchads.googleapis.com/v2/customers",
    "https://searchads.googleapis.com/v2/customers:listAccessibleCustomers",
]
CHANGELOG_FEEDS = [
    "https://developers.google.com/google-ads/api/docs/release-notes/feed",
]
DOCS_LINKS = [
    "https://developers.google.com/search-ads/api/",
    "https://developers.google.com/search-ads/api/docs/",
]

metadata = {
    "platform": "sa360",
    "auth_types": ["oauth2", "service_account"],
    "documentation_links": DOCS_LINKS,
    "declared_endpoints": DECLARED_ENDPOINTS,
    "sources_monitored": CHANGELOG_FEEDS,
    "data_collected": ["accessible customers for validation", "release notes feed"],
}


def token_checks(token: str, config: Any) -> list[CheckResult]:
    """Validate token via SA360 listAccessibleCustomers (Bearer)."""
    results: list[CheckResult] = []
    endpoint = "https://searchads.googleapis.com/v2/customers:listAccessibleCustomers"
    try:
        resp = get(endpoint, token=token, raise_for_status=False)
        if resp.status_code == 200:
            data = resp.json() if resp.content else {}
            names = data.get("resourceNames", [])
            count = len(names) if isinstance(names, list) else 0
            results.append(
                CheckResult(
                    name="validity",
                    status=CheckStatus.OK,
                    message=f"Token valid ({count} accessible customer(s))",
                    details={"count": count},
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
        events.extend(safe_fetch_feed(url, "sa360", since=since))
    return events


def collect_status() -> None:
    return None


plugin = type("SA360Plugin", (), {
    "metadata": metadata,
    "token_checks": lambda self, token, config: token_checks(token, config),
    "collect_changes": lambda self, since: collect_changes(since),
    "collect_status": lambda self: collect_status(),
})()
