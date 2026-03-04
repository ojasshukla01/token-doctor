"""
Salesforce plugin: token check via /services/oauth2/userinfo or /sobjects (Salesforce API).

Marketing Cloud uses different auth (tenant subdomain); this plugin targets core Salesforce REST.
"""

from __future__ import annotations

from typing import Any

from token_doctor.core.http_client import get
from token_doctor.core.schema import CheckResult, CheckStatus, NormalizedEvent
from token_doctor.platforms.base import safe_fetch_feed

# Instance URL is tenant-specific; profile option 'instance_url' or token response provides it
DECLARED_ENDPOINTS = [
    "https://login.salesforce.com/services/oauth2/userinfo",
    "https://{instance}.salesforce.com/services/oauth2/userinfo",
]
CHANGELOG_FEEDS = [
    "https://developer.salesforce.com/blogs/feed",
]
DOCS_LINKS = [
    "https://developer.salesforce.com/docs/apis",
    "https://developer.salesforce.com/blogs",
]

metadata = {
    "platform": "salesforce",
    "auth_types": ["oauth2", "jwt_bearer"],
    "documentation_links": DOCS_LINKS,
    "declared_endpoints": DECLARED_ENDPOINTS,
    "sources_monitored": CHANGELOG_FEEDS,
    "data_collected": ["userinfo (user_id, preferred_username) for validation", "developer blog feed"],
}


def _get_userinfo_url(config: Any) -> str:
    """Userinfo URL; use profile option instance_url if set (e.g. https://mycompany.my.salesforce.com)."""
    if config and getattr(config, "get_profile", None):
        profile = config.get_profile("salesforce")
        if profile and profile.options.get("instance_url"):
            base = profile.options["instance_url"].rstrip("/")
            return f"{base}/services/oauth2/userinfo"
    return "https://login.salesforce.com/services/oauth2/userinfo"


def token_checks(token: str, config: Any) -> list[CheckResult]:
    """Validate Salesforce OAuth token via userinfo (Bearer)."""
    results: list[CheckResult] = []
    endpoint = _get_userinfo_url(config)
    try:
        resp = get(endpoint, token=token, raise_for_status=False)
        if resp.status_code == 200:
            data = resp.json() if resp.content else {}
            name = data.get("preferred_username", data.get("user_id", "?"))
            results.append(
                CheckResult(
                    name="validity",
                    status=CheckStatus.OK,
                    message=f"Token valid (user: {name})",
                    details={"user_id": data.get("user_id")},
                    endpoint_used=endpoint,
                )
            )
        elif resp.status_code in (401, 403):
            results.append(
                CheckResult(
                    name="validity",
                    status=CheckStatus.ERROR,
                    message="Token invalid or expired. Set instance_url in profile if using custom domain.",
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
        events.extend(safe_fetch_feed(url, "salesforce", since=since))
    return events


def collect_status() -> None:
    return None


plugin = type("SalesforcePlugin", (), {
    "metadata": metadata,
    "token_checks": lambda self, token, config: token_checks(token, config),
    "collect_changes": lambda self, since: collect_changes(since),
    "collect_status": lambda self: collect_status(),
})()
