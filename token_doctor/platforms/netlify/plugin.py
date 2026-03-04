"""Netlify plugin: token check via /api/v1/user, changelog from blog."""

from __future__ import annotations

from typing import Any

from token_doctor.core.http_client import get
from token_doctor.core.schema import CheckResult, CheckStatus, NormalizedEvent
from token_doctor.platforms.base import safe_fetch_feed

DECLARED_ENDPOINTS = ["https://api.netlify.com/api/v1/user"]
CHANGELOG_FEEDS = [
    "https://www.netlify.com/blog/feed/",
]
DOCS_LINKS = ["https://docs.netlify.com/api/get-started/", "https://www.netlify.com/blog"]

metadata = {
    "platform": "netlify",
    "auth_types": ["oauth", "personal_access_token"],
    "documentation_links": DOCS_LINKS,
    "declared_endpoints": DECLARED_ENDPOINTS,
    "sources_monitored": CHANGELOG_FEEDS,
    "data_collected": ["user id, email from /user", "blog feed entries"],
}


def token_checks(token: str, config: Any) -> list[CheckResult]:
    """Validate token via Netlify /api/v1/user (Bearer)."""
    results: list[CheckResult] = []
    endpoint = "https://api.netlify.com/api/v1/user"
    try:
        resp = get(endpoint, token=token, raise_for_status=False)
        if resp.status_code == 200:
            data = resp.json() if resp.content else {}
            email = data.get("email", "?")
            results.append(
                CheckResult(
                    name="validity",
                    status=CheckStatus.OK,
                    message=f"Token valid (user: {email})",
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
        events.extend(safe_fetch_feed(url, "netlify", since=since))
    return events


def collect_status() -> None:
    return None


plugin = type("NetlifyPlugin", (), {
    "metadata": metadata,
    "token_checks": lambda self, token, config: token_checks(token, config),
    "collect_changes": lambda self, since: collect_changes(since),
    "collect_status": lambda self: collect_status(),
})()
