"""
Microsoft plugin: token check via Microsoft Graph /me.

Used for Azure AD, Microsoft 365, and SharePoint (Graph covers both).
"""

from __future__ import annotations

from typing import Any

from token_doctor.core.http_client import get
from token_doctor.core.schema import CheckResult, CheckStatus, NormalizedEvent
from token_doctor.platforms.base import safe_fetch_feed

DECLARED_ENDPOINTS = [
    "https://graph.microsoft.com/v1.0/me",
    "https://graph.microsoft.com/v1.0/sites/root",
]
CHANGELOG_FEEDS = [
    "https://devblogs.microsoft.com/microsoft365dev/feed/",
    "https://developer.microsoft.com/en-us/graph/blogs/feed/",
]
DOCS_LINKS = [
    "https://learn.microsoft.com/en-us/graph/api/user-get",
    "https://learn.microsoft.com/en-us/azure/active-directory/develop/",
]

metadata = {
    "platform": "microsoft",
    "auth_types": ["oauth2", "client_credentials", "on_behalf_of"],
    "documentation_links": DOCS_LINKS,
    "declared_endpoints": DECLARED_ENDPOINTS,
    "sources_monitored": CHANGELOG_FEEDS,
    "data_collected": ["user displayName, id from /me", "Microsoft 365/Graph blog feed"],
}


def token_checks(token: str, config: Any) -> list[CheckResult]:
    """Validate token via Microsoft Graph /v1.0/me (Bearer)."""
    results: list[CheckResult] = []
    endpoint = "https://graph.microsoft.com/v1.0/me"
    try:
        resp = get(endpoint, token=token, raise_for_status=False)
        if resp.status_code == 200:
            data = resp.json() if resp.content else {}
            name = data.get("displayName", data.get("userPrincipalName", "?"))
            results.append(
                CheckResult(
                    name="validity",
                    status=CheckStatus.OK,
                    message=f"Token valid (user: {name})",
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
        events.extend(safe_fetch_feed(url, "microsoft", since=since))
    return events


def collect_status() -> None:
    return None


plugin = type("MicrosoftPlugin", (), {
    "metadata": metadata,
    "token_checks": lambda self, token, config: token_checks(token, config),
    "collect_changes": lambda self, since: collect_changes(since),
    "collect_status": lambda self: collect_status(),
})()
