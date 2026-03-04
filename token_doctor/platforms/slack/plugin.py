"""Slack plugin: token check via auth.test, changelog from developer docs."""

from __future__ import annotations

from typing import Any

from token_doctor.core.http_client import post
from token_doctor.core.schema import CheckResult, CheckStatus, NormalizedEvent
from token_doctor.platforms.base import safe_fetch_feed

DECLARED_ENDPOINTS = ["https://slack.com/api/auth.test"]
CHANGELOG_FEEDS = [
    "https://api.slack.com/changelog/feed",  # if exists; else blog
]
DOCS_LINKS = ["https://api.slack.com/methods/auth.test", "https://api.slack.com/changelog"]

metadata = {
    "platform": "slack",
    "auth_types": ["bot", "user", "legacy"],
    "documentation_links": DOCS_LINKS,
    "declared_endpoints": DECLARED_ENDPOINTS,
    "sources_monitored": CHANGELOG_FEEDS,
    "data_collected": ["auth.test result (ok, user, team)", "changelog entries from RSS"],
}


def token_checks(token: str, config: Any) -> list[CheckResult]:
    """Validate token via Slack auth.test (POST)."""
    results: list[CheckResult] = []
    endpoint = "https://slack.com/api/auth.test"
    try:
        # Slack uses Bearer for bot/user tokens
        resp = post(endpoint, token=token, json={}, raise_for_status=False)
        data = resp.json() if resp.content else {}
        ok = data.get("ok") is True
        if ok:
            user = data.get("user", "?")
            team = data.get("team", "?")
            results.append(
                CheckResult(
                    name="validity",
                    status=CheckStatus.OK,
                    message=f"Token valid (user: {user}, team: {team})",
                    details={"user": user, "team": team},
                    endpoint_used=endpoint,
                )
            )
        else:
            err = data.get("error", "unknown")
            results.append(
                CheckResult(
                    name="validity",
                    status=CheckStatus.ERROR,
                    message=f"Slack API error: {err}",
                    details={"error": err},
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
        events.extend(safe_fetch_feed(url, "slack", since=since))
    return events


def collect_status() -> None:
    return None


plugin = type("SlackPlugin", (), {
    "metadata": metadata,
    "token_checks": lambda self, token, config: token_checks(token, config),
    "collect_changes": lambda self, since: collect_changes(since),
    "collect_status": lambda self: collect_status(),
})()
