"""
Meta Messenger plugin: token check via Graph API (Page or App scoped).

Messenger Platform uses Facebook Graph; validate via /me or /me/accounts.
"""

from __future__ import annotations

from typing import Any

from token_doctor.core.http_client import get
from token_doctor.core.schema import CheckResult, CheckStatus, NormalizedEvent
from token_doctor.platforms.base import safe_fetch_feed

DECLARED_ENDPOINTS = [
    "https://graph.facebook.com/v21.0/me",
    "https://graph.facebook.com/v21.0/me/accounts",
]
CHANGELOG_FEEDS = [
    "https://developers.facebook.com/blog/feed/",
]
DOCS_LINKS = [
    "https://developers.facebook.com/docs/messenger-platform/",
    "https://developers.facebook.com/blog",
]

metadata = {
    "platform": "meta_messenger",
    "auth_types": ["oauth2", "page_token"],
    "documentation_links": DOCS_LINKS,
    "declared_endpoints": DECLARED_ENDPOINTS,
    "sources_monitored": CHANGELOG_FEEDS,
    "data_collected": ["me (id, name) for validation", "Meta developer blog feed"],
}


def token_checks(token: str, config: Any) -> list[CheckResult]:
    """Validate token via Facebook Graph /me (Bearer)."""
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
                    message=f"Token valid (user/app: {name})",
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
        events.extend(safe_fetch_feed(url, "meta_messenger", since=since))
    return events


def collect_status() -> None:
    return None


plugin = type("MetaMessengerPlugin", (), {
    "metadata": metadata,
    "token_checks": lambda self, token, config: token_checks(token, config),
    "collect_changes": lambda self, since: collect_changes(since),
    "collect_status": lambda self: collect_status(),
})()
