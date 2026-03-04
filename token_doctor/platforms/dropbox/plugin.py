"""Dropbox plugin: token check via /2/users/get_current_account, changelog from blog."""

from __future__ import annotations

from typing import Any

from token_doctor.core.http_client import post
from token_doctor.core.schema import CheckResult, CheckStatus, NormalizedEvent
from token_doctor.platforms.base import safe_fetch_feed

DECLARED_ENDPOINTS = ["https://api.dropboxapi.com/2/users/get_current_account"]
CHANGELOG_FEEDS = [
    "https://blog.dropbox.com/feed/",
    "https://www.dropbox.com/developers/documentation/feed",  # if exists
]
DOCS_LINKS = ["https://www.dropbox.com/developers/documentation", "https://blog.dropbox.com"]

metadata = {
    "platform": "dropbox",
    "auth_types": ["oauth2", "app_token"],
    "documentation_links": DOCS_LINKS,
    "declared_endpoints": DECLARED_ENDPOINTS,
    "sources_monitored": CHANGELOG_FEEDS,
    "data_collected": ["account id, name from get_current_account", "blog feed entries"],
}


def token_checks(token: str, config: Any) -> list[CheckResult]:
    """Validate token via Dropbox POST /2/users/get_current_account (null body)."""
    results: list[CheckResult] = []
    endpoint = "https://api.dropboxapi.com/2/users/get_current_account"
    try:
        resp = post(
            endpoint,
            token=token,
            json={},
            headers={"Content-Type": "application/json"},
            raise_for_status=False,
        )
        if resp.status_code == 200:
            data = resp.json() if resp.content else {}
            name = data.get("name", {}).get("display_name", "?")
            results.append(
                CheckResult(
                    name="validity",
                    status=CheckStatus.OK,
                    message=f"Token valid (account: {name})",
                    details={"account_id": data.get("account_id")},
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
        events.extend(safe_fetch_feed(url, "dropbox", since=since))
    return events


def collect_status() -> None:
    return None


plugin = type("DropboxPlugin", (), {
    "metadata": metadata,
    "token_checks": lambda self, token, config: token_checks(token, config),
    "collect_changes": lambda self, since: collect_changes(since),
    "collect_status": lambda self: collect_status(),
})()
