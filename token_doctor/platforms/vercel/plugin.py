"""Vercel plugin: token check via /v2/user, changelog from blog feed."""

from __future__ import annotations

from typing import Any

from token_doctor.core.http_client import get
from token_doctor.core.schema import CheckResult, CheckStatus, NormalizedEvent
from token_doctor.platforms.base import safe_fetch_feed

DECLARED_ENDPOINTS = ["https://api.vercel.com/v2/user"]
CHANGELOG_FEEDS = [
    "https://vercel.com/blog/feed",
    "https://vercel.com/changelog/feed",  # if exists
]
DOCS_LINKS = ["https://vercel.com/docs/rest-api", "https://vercel.com/changelog"]

metadata = {
    "platform": "vercel",
    "auth_types": ["oauth", "api_token"],
    "documentation_links": DOCS_LINKS,
    "declared_endpoints": DECLARED_ENDPOINTS,
    "sources_monitored": CHANGELOG_FEEDS,
    "data_collected": ["user id, username from /v2/user", "blog/changelog feed entries"],
}


def token_checks(token: str, config: Any) -> list[CheckResult]:
    """Validate token via Vercel /v2/user."""
    results: list[CheckResult] = []
    endpoint = "https://api.vercel.com/v2/user"
    try:
        resp = get(endpoint, token=token, raise_for_status=False)
        if resp.status_code == 200:
            data = resp.json() if resp.content else {}
            username = data.get("username", data.get("name", "?"))
            results.append(
                CheckResult(
                    name="validity",
                    status=CheckStatus.OK,
                    message=f"Token valid (user: {username})",
                    details={"username": username, "id": data.get("id")},
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
        events.extend(safe_fetch_feed(url, "vercel", since=since))
    return events


def collect_status() -> None:
    return None


plugin = type("VercelPlugin", (), {
    "metadata": metadata,
    "token_checks": lambda self, token, config: token_checks(token, config),
    "collect_changes": lambda self, since: collect_changes(since),
    "collect_status": lambda self: collect_status(),
})()
