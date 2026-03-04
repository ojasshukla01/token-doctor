"""
Adobe plugin: token check via userinfo (IMS) or Admin API.

Supports Adobe IMS OAuth; declared endpoints for userinfo and developer feeds.
"""

from __future__ import annotations

from typing import Any

from token_doctor.core.http_client import get
from token_doctor.core.schema import CheckResult, CheckStatus, NormalizedEvent
from token_doctor.platforms.base import safe_fetch_feed

DECLARED_ENDPOINTS = [
    "https://ims-na1.adobelogin.com/ims/userinfo",
    "https://usermanagement.adobe.io/v2/usermanagement/users/me",
]
CHANGELOG_FEEDS = [
    "https://developer.adobe.com/feed.xml",
]
DOCS_LINKS = [
    "https://developer.adobe.com/",
    "https://experienceleague.adobe.com/docs/developer.html",
]

metadata = {
    "platform": "adobe",
    "auth_types": ["oauth2", "service_account", "jwt"],
    "documentation_links": DOCS_LINKS,
    "declared_endpoints": DECLARED_ENDPOINTS,
    "sources_monitored": CHANGELOG_FEEDS,
    "data_collected": ["userinfo (name, email) for validation", "developer blog feed"],
}


def token_checks(token: str, config: Any) -> list[CheckResult]:
    """Validate Adobe IMS token via userinfo endpoint (Bearer)."""
    results: list[CheckResult] = []
    endpoint = "https://ims-na1.adobelogin.com/ims/userinfo"
    try:
        resp = get(endpoint, token=token, raise_for_status=False)
        if resp.status_code == 200:
            data = resp.json() if resp.content else {}
            name = data.get("name", data.get("email", "?"))
            results.append(
                CheckResult(
                    name="validity",
                    status=CheckStatus.OK,
                    message=f"Token valid (user: {name})",
                    details={"sub": data.get("sub")},
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
        events.extend(safe_fetch_feed(url, "adobe", since=since))
    return events


def collect_status() -> None:
    return None


plugin = type("AdobePlugin", (), {
    "metadata": metadata,
    "token_checks": lambda self, token, config: token_checks(token, config),
    "collect_changes": lambda self, since: collect_changes(since),
    "collect_status": lambda self: collect_status(),
})()
