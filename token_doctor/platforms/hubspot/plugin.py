"""
HubSpot plugin: token check via CRM API (account or contacts).

Supports private app access tokens and OAuth; uses /crm/v3/objects/contacts (limit=1) or account.
"""

from __future__ import annotations

from typing import Any

from token_doctor.core.http_client import get
from token_doctor.core.schema import CheckResult, CheckStatus, NormalizedEvent
from token_doctor.platforms.base import safe_fetch_feed

DECLARED_ENDPOINTS = [
    "https://api.hubapi.com/account-info/v3/details",
    "https://api.hubapi.com/crm/v3/objects/contacts",
]
CHANGELOG_FEEDS = [
    "https://developers.hubspot.com/blog/feed",
]
DOCS_LINKS = [
    "https://developers.hubspot.com/docs/api/overview",
    "https://developers.hubspot.com/blog",
]

metadata = {
    "platform": "hubspot",
    "auth_types": ["private_app", "oauth2"],
    "documentation_links": DOCS_LINKS,
    "declared_endpoints": DECLARED_ENDPOINTS,
    "sources_monitored": CHANGELOG_FEEDS,
    "data_collected": ["account details or CRM object list for validation", "developer blog feed"],
}


def token_checks(token: str, config: Any) -> list[CheckResult]:
    """Validate token via HubSpot account-info or CRM API (Bearer)."""
    results: list[CheckResult] = []
    endpoint = "https://api.hubapi.com/account-info/v3/details"
    try:
        resp = get(endpoint, token=token, raise_for_status=False)
        if resp.status_code == 200:
            data = resp.json() if resp.content else {}
            name = data.get("name", data.get("portalId", "?"))
            results.append(
                CheckResult(
                    name="validity",
                    status=CheckStatus.OK,
                    message=f"Token valid (account: {name})",
                    details={"portalId": data.get("portalId")},
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
        events.extend(safe_fetch_feed(url, "hubspot", since=since))
    return events


def collect_status() -> None:
    return None


plugin = type("HubSpotPlugin", (), {
    "metadata": metadata,
    "token_checks": lambda self, token, config: token_checks(token, config),
    "collect_changes": lambda self, since: collect_changes(since),
    "collect_status": lambda self: collect_status(),
})()
