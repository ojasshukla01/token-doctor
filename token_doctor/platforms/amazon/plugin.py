"""
Amazon plugin: token/credential check via Amazon Ads API or STS GetCallerIdentity.

Uses Amazon Ads API profile endpoint when token is an Ads API token;
otherwise can skip or use STS (requires AWS SDK pattern). Declared endpoints for transparency.
"""

from __future__ import annotations

from typing import Any

from token_doctor.core.http_client import get
from token_doctor.core.schema import CheckResult, CheckStatus, NormalizedEvent
from token_doctor.platforms.base import safe_fetch_feed

# Amazon Ads API (advertising.amazon.com) - profile or account endpoint
DECLARED_ENDPOINTS = [
    "https://advertising-api.amazon.com/v2/profiles",
    "https://advertising-api-test.amazon.com/v2/profiles",
]
CHANGELOG_FEEDS = [
    "https://developer-docs.amazon.com/amazon-advertising-api/feed",
    "https://aws.amazon.com/blogs/developer/feed/",
]
DOCS_LINKS = [
    "https://developer-docs.amazon.com/amazon-advertising-api/",
    "https://docs.aws.amazon.com/",
]

metadata = {
    "platform": "amazon",
    "auth_types": ["oauth2", "lwa_refresh", "sts"],
    "documentation_links": DOCS_LINKS,
    "declared_endpoints": DECLARED_ENDPOINTS,
    "sources_monitored": CHANGELOG_FEEDS,
    "data_collected": ["profiles list for Ads API", "developer/blog feed entries"],
}


def token_checks(token: str, config: Any) -> list[CheckResult]:
    """Validate Amazon Ads API token via GET /v2/profiles (Bearer)."""
    results: list[CheckResult] = []
    endpoint = "https://advertising-api.amazon.com/v2/profiles"
    try:
        headers = {}
        if config and getattr(config, "get_profile", None):
            profile = config.get_profile("amazon")
            if profile and profile.options.get("client_id"):
                headers["Amazon-Advertising-API-ClientId"] = profile.options["client_id"]
        resp = get(endpoint, token=token, headers=headers or None, raise_for_status=False)
        if resp.status_code == 200:
            data = resp.json() if resp.content else {}
            profiles = data if isinstance(data, list) else data.get("profiles", [])
            count = len(profiles) if isinstance(profiles, list) else 0
            results.append(
                CheckResult(
                    name="validity",
                    status=CheckStatus.OK,
                    message=f"Token valid ({count} profile(s))",
                    details={"count": count},
                    endpoint_used=endpoint,
                )
            )
        elif resp.status_code in (401, 403):
            results.append(
                CheckResult(
                    name="validity",
                    status=CheckStatus.ERROR,
                    message="Token invalid or expired. Ensure client_id in profile options if required.",
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
        events.extend(safe_fetch_feed(url, "amazon", since=since))
    return events


def collect_status() -> None:
    return None


plugin = type("AmazonPlugin", (), {
    "metadata": metadata,
    "token_checks": lambda self, token, config: token_checks(token, config),
    "collect_changes": lambda self, since: collect_changes(since),
    "collect_status": lambda self: collect_status(),
})()
