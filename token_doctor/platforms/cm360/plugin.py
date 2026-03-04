"""
Campaign Manager 360 plugin: token check via DFA Reporting API userprofiles list.

Google Marketing Platform; OAuth 2.0. No simple /me; use userprofiles or similar.
"""

from __future__ import annotations

from typing import Any

from token_doctor.core.http_client import get
from token_doctor.core.schema import CheckResult, CheckStatus, NormalizedEvent
from token_doctor.platforms.base import safe_fetch_feed

# DCM/DFA Reporting API
DECLARED_ENDPOINTS = [
    "https://dfareporting.googleapis.com/dfareporting/v4/userprofiles",
]
CHANGELOG_FEEDS = [
    "https://developers.google.com/google-ads/api/docs/release-notes/feed",
]
DOCS_LINKS = [
    "https://developers.google.com/doubleclick-advertisers/",
    "https://developers.google.com/doubleclick-advertisers/api/v4/userprofiles/list",
]

metadata = {
    "platform": "cm360",
    "auth_types": ["oauth2", "service_account"],
    "documentation_links": DOCS_LINKS,
    "declared_endpoints": DECLARED_ENDPOINTS,
    "sources_monitored": CHANGELOG_FEEDS,
    "data_collected": ["userprofiles list for validation", "release notes feed"],
}


def token_checks(token: str, config: Any) -> list[CheckResult]:
    """Validate token via DFA Reporting userprofiles list (Bearer)."""
    results: list[CheckResult] = []
    endpoint = "https://dfareporting.googleapis.com/dfareporting/v4/userprofiles"
    try:
        resp = get(endpoint, token=token, raise_for_status=False)
        if resp.status_code == 200:
            data = resp.json() if resp.content else {}
            items = data.get("items", data) if isinstance(data, dict) else data
            count = len(items) if isinstance(items, list) else 0
            results.append(
                CheckResult(
                    name="validity",
                    status=CheckStatus.OK,
                    message=f"Token valid ({count} user profile(s))",
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
        events.extend(safe_fetch_feed(url, "cm360", since=since))
    return events


def collect_status() -> None:
    return None


plugin = type("CM360Plugin", (), {
    "metadata": metadata,
    "token_checks": lambda self, token, config: token_checks(token, config),
    "collect_changes": lambda self, since: collect_changes(since),
    "collect_status": lambda self: collect_status(),
})()
