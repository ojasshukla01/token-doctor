"""SendGrid plugin: token check via /v3/user/account, changelog from blog."""

from __future__ import annotations

from typing import Any

from token_doctor.core.http_client import get
from token_doctor.core.schema import CheckResult, CheckStatus, NormalizedEvent
from token_doctor.platforms.base import safe_fetch_feed

DECLARED_ENDPOINTS = ["https://api.sendgrid.com/v3/user/account"]
CHANGELOG_FEEDS = [
    "https://sendgrid.com/blog/feed/",
]
DOCS_LINKS = ["https://docs.sendgrid.com/", "https://sendgrid.com/blog"]

metadata = {
    "platform": "sendgrid",
    "auth_types": ["api_key"],
    "documentation_links": DOCS_LINKS,
    "declared_endpoints": DECLARED_ENDPOINTS,
    "sources_monitored": CHANGELOG_FEEDS,
    "data_collected": ["user/account from /v3/user/account", "blog feed entries"],
}


def token_checks(token: str, config: Any) -> list[CheckResult]:
    """Validate API key via SendGrid /v3/user/account (Bearer)."""
    results: list[CheckResult] = []
    endpoint = "https://api.sendgrid.com/v3/user/account"
    try:
        resp = get(endpoint, token=token, raise_for_status=False)
        if resp.status_code == 200:
            data = resp.json() if resp.content else {}
            user = data.get("user", {}) or data
            email = user.get("email", data.get("email", "?"))
            results.append(
                CheckResult(
                    name="validity",
                    status=CheckStatus.OK,
                    message=f"API key valid (account: {email})",
                    details={"email": email},
                    endpoint_used=endpoint,
                )
            )
        elif resp.status_code in (401, 403):
            results.append(
                CheckResult(
                    name="validity",
                    status=CheckStatus.ERROR,
                    message="API key invalid or unauthorized",
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
        events.extend(safe_fetch_feed(url, "sendgrid", since=since))
    return events


def collect_status() -> None:
    return None


plugin = type("SendGridPlugin", (), {
    "metadata": metadata,
    "token_checks": lambda self, token, config: token_checks(token, config),
    "collect_changes": lambda self, since: collect_changes(since),
    "collect_status": lambda self: collect_status(),
})()
