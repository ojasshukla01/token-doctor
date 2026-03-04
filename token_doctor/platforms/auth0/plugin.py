"""Auth0 plugin: token check via /userinfo (OAuth access token), changelog from blog."""

from __future__ import annotations

from typing import Any

from token_doctor.core.http_client import get
from token_doctor.core.schema import CheckResult, CheckStatus, NormalizedEvent
from token_doctor.platforms.base import safe_fetch_feed

# Userinfo endpoint is tenant-specific: https://<tenant>.auth0.com/userinfo
# Token stored is access token; tenant can be in profile options.
DECLARED_ENDPOINTS = ["https://{tenant}.auth0.com/userinfo"]
CHANGELOG_FEEDS = [
    "https://auth0.com/blog/feed/",
]
DOCS_LINKS = ["https://auth0.com/docs/api/authentication", "https://auth0.com/blog"]

metadata = {
    "platform": "auth0",
    "auth_types": ["oauth_access_token", "management_api_token"],
    "documentation_links": DOCS_LINKS,
    "declared_endpoints": DECLARED_ENDPOINTS,
    "sources_monitored": CHANGELOG_FEEDS,
    "data_collected": ["userinfo sub, name for validation", "blog feed entries"],
}


def token_checks(token: str, config: Any) -> list[CheckResult]:
    """Validate access token via Auth0 /userinfo. Tenant from profile option 'tenant' (e.g. mycompany)."""
    results: list[CheckResult] = []
    tenant = "auth0"
    if config and getattr(config, "get_profile", None):
        profile = config.get_profile("auth0")
        if profile and profile.options.get("tenant"):
            tenant = profile.options["tenant"].strip()
    endpoint = f"https://{tenant}.auth0.com/userinfo"
    try:
        resp = get(endpoint, token=token, raise_for_status=False)
        if resp.status_code == 200:
            data = resp.json() if resp.content else {}
            name = data.get("name", data.get("email", data.get("sub", "?")))
            results.append(
                CheckResult(
                    name="validity",
                    status=CheckStatus.OK,
                    message=f"Token valid (user: {name})",
                    details={"sub": data.get("sub")},
                    endpoint_used=endpoint,
                )
            )
        elif resp.status_code in (401, 403):
            results.append(
                CheckResult(
                    name="validity",
                    status=CheckStatus.ERROR,
                    message="Token invalid or expired. Check tenant option.",
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
        events.extend(safe_fetch_feed(url, "auth0", since=since))
    return events


def collect_status() -> None:
    return None


plugin = type("Auth0Plugin", (), {
    "metadata": metadata,
    "token_checks": lambda self, token, config: token_checks(token, config),
    "collect_changes": lambda self, since: collect_changes(since),
    "collect_status": lambda self: collect_status(),
})()
