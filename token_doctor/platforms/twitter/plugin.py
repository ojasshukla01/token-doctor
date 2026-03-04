"""
Twitter / X plugin: token check via API v2 /2/users/me.

OAuth 2.0 Bearer token (or OAuth 1.0 user context); declared endpoints and developer blog.
"""

from __future__ import annotations

from typing import Any

from token_doctor.core.http_client import get
from token_doctor.core.schema import CheckResult, CheckStatus, NormalizedEvent
from token_doctor.platforms.base import safe_fetch_feed

DECLARED_ENDPOINTS = [
    "https://api.twitter.com/2/users/me",
    "https://api.x.com/2/users/me",
]
CHANGELOG_FEEDS = [
    "https://blog.twitter.com/developer/en_us/blog/feed",
    "https://developer.twitter.com/en/blog/feed",
]
DOCS_LINKS = [
    "https://developer.twitter.com/en/docs/twitter-api",
    "https://developer.x.com/en/docs",
]

metadata = {
    "platform": "twitter",
    "auth_types": ["oauth2", "oauth1a", "bearer"],
    "documentation_links": DOCS_LINKS,
    "declared_endpoints": DECLARED_ENDPOINTS,
    "sources_monitored": CHANGELOG_FEEDS,
    "data_collected": ["user id, username from /users/me", "developer blog feed"],
}


def token_checks(token: str, config: Any) -> list[CheckResult]:
    """Validate token via Twitter API v2 /2/users/me (Bearer)."""
    results: list[CheckResult] = []
    endpoint = "https://api.twitter.com/2/users/me"
    try:
        resp = get(endpoint, token=token, raise_for_status=False)
        if resp.status_code == 200:
            data = resp.json() if resp.content else {}
            ud = data.get("data", data)
            name = ud.get("username", ud.get("name", "?"))
            results.append(
                CheckResult(
                    name="validity",
                    status=CheckStatus.OK,
                    message=f"Token valid (user: {name})",
                    details={"id": ud.get("id")},
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
        events.extend(safe_fetch_feed(url, "twitter", since=since))
    return events


def collect_status() -> None:
    return None


plugin = type("TwitterPlugin", (), {
    "metadata": metadata,
    "token_checks": lambda self, token, config: token_checks(token, config),
    "collect_changes": lambda self, since: collect_changes(since),
    "collect_status": lambda self: collect_status(),
})()
