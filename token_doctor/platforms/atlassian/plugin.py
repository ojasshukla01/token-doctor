"""Atlassian plugin: token check via Jira /rest/api/3/myself, changelog from developer blog."""

from __future__ import annotations

from typing import Any

from token_doctor.core.http_client import get
from token_doctor.core.schema import CheckResult, CheckStatus, NormalizedEvent
from token_doctor.platforms.base import safe_fetch_feed

# User must configure base URL (e.g. https://your-domain.atlassian.net)
DECLARED_ENDPOINTS = ["{base_url}/rest/api/3/myself"]
CHANGELOG_FEEDS = [
    "https://developer.atlassian.com/cloud/jira/platform/feed/",
    "https://confluence.atlassian.com/feeds/allposts.xml",
]
DOCS_LINKS = [
    "https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-myself/",
    "https://developer.atlassian.com/blog",
]

metadata = {
    "platform": "atlassian",
    "auth_types": ["oauth", "api_token", "personal_access_token"],
    "documentation_links": DOCS_LINKS,
    "declared_endpoints": DECLARED_ENDPOINTS,
    "sources_monitored": CHANGELOG_FEEDS,
    "data_collected": ["current user from /rest/api/3/myself", "developer blog feed entries"],
}


def token_checks(token: str, config: Any) -> list[CheckResult]:
    """
    Validate token via Jira /rest/api/3/myself.
    If config has base_url in profile options, use it; else default to atlassian.net (requires site).
    """
    results: list[CheckResult] = []
    # Default placeholder; set profile option base_url (e.g. https://your-site.atlassian.net) for real check.
    base_url = "https://example.atlassian.net"
    if config and getattr(config, "get_profile", None):
        profile = config.get_profile("atlassian")
        if profile and profile.options.get("base_url"):
            base_url = (profile.options["base_url"] or "").rstrip("/") or base_url
    endpoint = f"{base_url}/rest/api/3/myself"
    try:
        resp = get(endpoint, token=token, raise_for_status=False)
        if resp.status_code == 200:
            data = resp.json() if resp.content else {}
            name = data.get("displayName", data.get("name", "?"))
            results.append(
                CheckResult(
                    name="validity",
                    status=CheckStatus.OK,
                    message=f"Token valid (user: {name})",
                    details={"accountId": data.get("accountId")},
                    endpoint_used=endpoint,
                )
            )
        elif resp.status_code in (401, 403):
            results.append(
                CheckResult(
                    name="validity",
                    status=CheckStatus.ERROR,
                    message="Token invalid or expired. Ensure base_url is set for your Jira site.",
                    endpoint_used=endpoint,
                )
            )
        else:
            results.append(
                CheckResult(
                    name="validity",
                    status=CheckStatus.WARNING,
                    message=f"Unexpected status {resp.status_code}. Check base_url (e.g. https://your-site.atlassian.net).",
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
        events.extend(safe_fetch_feed(url, "atlassian", since=since))
    return events


def collect_status() -> None:
    return None


plugin = type("AtlassianPlugin", (), {
    "metadata": metadata,
    "token_checks": lambda self, token, config: token_checks(token, config),
    "collect_changes": lambda self, since: collect_changes(since),
    "collect_status": lambda self: collect_status(),
})()
