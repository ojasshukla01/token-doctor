"""
SharePoint plugin: token check via Microsoft Graph sites/root.

Uses same Microsoft Graph token as microsoft plugin; validates SharePoint access.
"""

from __future__ import annotations

from typing import Any

from token_doctor.core.http_client import get
from token_doctor.core.schema import CheckResult, CheckStatus, NormalizedEvent
from token_doctor.platforms.base import safe_fetch_feed

DECLARED_ENDPOINTS = [
    "https://graph.microsoft.com/v1.0/sites/root",
    "https://graph.microsoft.com/v1.0/me",
]
CHANGELOG_FEEDS = [
    "https://devblogs.microsoft.com/microsoft365dev/feed/",
]
DOCS_LINKS = [
    "https://learn.microsoft.com/en-us/graph/api/resources/sharepoint",
    "https://learn.microsoft.com/en-us/sharepoint/dev/",
]

metadata = {
    "platform": "sharepoint",
    "auth_types": ["oauth2"],
    "documentation_links": DOCS_LINKS,
    "declared_endpoints": DECLARED_ENDPOINTS,
    "sources_monitored": CHANGELOG_FEEDS,
    "data_collected": ["sites/root for SharePoint access", "Microsoft 365 dev blog feed"],
}


def token_checks(token: str, config: Any) -> list[CheckResult]:
    """Validate token via Graph GET /sites/root (Bearer)."""
    results: list[CheckResult] = []
    endpoint = "https://graph.microsoft.com/v1.0/sites/root"
    try:
        resp = get(endpoint, token=token, raise_for_status=False)
        if resp.status_code == 200:
            data = resp.json() if resp.content else {}
            name = data.get("displayName", data.get("name", "?"))
            results.append(
                CheckResult(
                    name="validity",
                    status=CheckStatus.OK,
                    message=f"Token valid (site: {name})",
                    details={"id": data.get("id")},
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
        events.extend(safe_fetch_feed(url, "sharepoint", since=since))
    return events


def collect_status() -> None:
    return None


plugin = type("SharePointPlugin", (), {
    "metadata": metadata,
    "token_checks": lambda self, token, config: token_checks(token, config),
    "collect_changes": lambda self, since: collect_changes(since),
    "collect_status": lambda self: collect_status(),
})()
