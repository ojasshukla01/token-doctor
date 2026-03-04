"""
Microsoft Advertising (Bing Ads) plugin: token check via Customer Management API.

OAuth 2.0; GetUser returns current user. Declared endpoints and changelog.
"""

from __future__ import annotations

from typing import Any

from token_doctor.core.schema import CheckResult, CheckStatus, NormalizedEvent
from token_doctor.platforms.base import safe_fetch_feed

# Bing Ads API is SOAP or REST; REST uses https://api.ads.microsoft.com
DECLARED_ENDPOINTS = [
    "https://api.ads.microsoft.com/v13/CustomerManagementService.svc",
    "https://login.microsoftonline.com/common/oauth2/v2.0/token",
]
CHANGELOG_FEEDS = [
    "https://ads.microsoft.com/blog/feed",
]
DOCS_LINKS = [
    "https://learn.microsoft.com/en-us/advertising/",
    "https://ads.microsoft.com/blog",
]

metadata = {
    "platform": "bing_ads",
    "auth_types": ["oauth2"],
    "documentation_links": DOCS_LINKS,
    "declared_endpoints": DECLARED_ENDPOINTS,
    "sources_monitored": CHANGELOG_FEEDS,
    "data_collected": ["Customer Management or reporting for validation", "blog feed"],
}


def token_checks(token: str, config: Any) -> list[CheckResult]:
    """Microsoft Advertising uses OAuth; no simple REST /me. Skip with message and docs."""
    results: list[CheckResult] = []
    results.append(
        CheckResult(
            name="validity",
            status=CheckStatus.SKIPPED,
            message="Bing Ads token check not implemented in MVP; use Microsoft Advertising API docs.",
            endpoint_used="",
        )
    )
    return results


def collect_changes(since: Any) -> list[NormalizedEvent]:
    events: list[NormalizedEvent] = []
    for url in CHANGELOG_FEEDS:
        events.extend(safe_fetch_feed(url, "bing_ads", since=since))
    return events


def collect_status() -> None:
    return None


plugin = type("BingAdsPlugin", (), {
    "metadata": metadata,
    "token_checks": lambda self, token, config: token_checks(token, config),
    "collect_changes": lambda self, since: collect_changes(since),
    "collect_status": lambda self: collect_status(),
})()
