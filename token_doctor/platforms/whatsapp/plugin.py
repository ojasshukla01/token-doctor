"""
WhatsApp plugin: token check via Cloud API or Graph (Meta).

WhatsApp Business API Cloud uses Graph API for app-level; On-Premises uses different endpoint.
Declared endpoints for transparency.
"""

from __future__ import annotations

from typing import Any

from token_doctor.core.http_client import get
from token_doctor.core.schema import CheckResult, CheckStatus, NormalizedEvent
from token_doctor.platforms.base import safe_fetch_feed

# Cloud API: Graph; On-Premises has different base URL
DECLARED_ENDPOINTS = [
    "https://graph.facebook.com/v21.0/me",
    "https://graph.facebook.com/v21.0/{phone-number-id}",
]
CHANGELOG_FEEDS = [
    "https://developers.facebook.com/blog/feed/",
]
DOCS_LINKS = [
    "https://developers.facebook.com/docs/whatsapp/cloud-api/",
    "https://developers.facebook.com/blog",
]

metadata = {
    "platform": "whatsapp",
    "auth_types": ["oauth2", "system_user", "permanent_token"],
    "documentation_links": DOCS_LINKS,
    "declared_endpoints": DECLARED_ENDPOINTS,
    "sources_monitored": CHANGELOG_FEEDS,
    "data_collected": ["Graph /me for app validation", "Meta developer blog feed"],
}


def token_checks(token: str, config: Any) -> list[CheckResult]:
    """Validate token via Facebook Graph /me (Bearer) — same as Meta Marketing/Messenger."""
    results: list[CheckResult] = []
    endpoint = "https://graph.facebook.com/v21.0/me"
    try:
        resp = get(endpoint, token=token, raise_for_status=False)
        if resp.status_code == 200:
            data = resp.json() if resp.content else {}
            name = data.get("name", data.get("id", "?"))
            results.append(
                CheckResult(
                    name="validity",
                    status=CheckStatus.OK,
                    message=f"Token valid (app: {name})",
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
        events.extend(safe_fetch_feed(url, "whatsapp", since=since))
    return events


def collect_status() -> None:
    return None


plugin = type("WhatsAppPlugin", (), {
    "metadata": metadata,
    "token_checks": lambda self, token, config: token_checks(token, config),
    "collect_changes": lambda self, since: collect_changes(since),
    "collect_status": lambda self: collect_status(),
})()
