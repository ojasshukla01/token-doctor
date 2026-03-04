"""
Mailchimp plugin: token check via GET /3.0/ping (Basic auth or OAuth).

API key format may include datacenter (e.g. key-us1); profile option 'dc' (e.g. us1) sets base URL.
"""

from __future__ import annotations

import base64
from typing import Any

from token_doctor.core.http_client import get
from token_doctor.core.schema import CheckResult, CheckStatus, NormalizedEvent
from token_doctor.platforms.base import safe_fetch_feed

# Base URL uses datacenter: https://{dc}.api.mailchimp.com/3.0
DECLARED_ENDPOINTS = ["https://{dc}.api.mailchimp.com/3.0/ping"]
CHANGELOG_FEEDS = [
    "https://mailchimp.com/developer/blog/feed/",
]
DOCS_LINKS = [
    "https://mailchimp.com/developer/marketing/api/",
    "https://mailchimp.com/developer/blog/",
]

metadata = {
    "platform": "mailchimp",
    "auth_types": ["api_key", "oauth2"],
    "documentation_links": DOCS_LINKS,
    "declared_endpoints": DECLARED_ENDPOINTS,
    "sources_monitored": CHANGELOG_FEEDS,
    "data_collected": ["ping health for validation", "developer blog feed"],
}


def _get_dc(token: str, config: Any) -> str:
    """Extract datacenter from profile option or from API key (e.g. key-us1 -> us1)."""
    if config and getattr(config, "get_profile", None):
        profile = config.get_profile("mailchimp")
        if profile and profile.options.get("dc"):
            raw = profile.options["dc"]
            return str(raw).strip().lower() if raw else "us1"
    if "-" in token and len(token) > 10:
        part = token.split("-")[-1]
        if len(part) in (2, 3) and part.isalpha():
            return part.lower()
    return "us1"


def token_checks(token: str, config: Any) -> list[CheckResult]:
    """Validate via Mailchimp GET /3.0/ping. Token as API key (Basic anystring:key) or Bearer for OAuth."""
    results: list[CheckResult] = []
    dc = _get_dc(token, config)
    base = f"https://{dc}.api.mailchimp.com"
    endpoint = f"{base}/3.0/ping"
    try:
        # Mailchimp: Basic auth (anystring:apikey) for API key, or Bearer for OAuth
        if token.strip().lower().startswith("bearer "):
            resp = get(endpoint, token=token.strip()[7:].strip(), raise_for_status=False)
        else:
            auth = base64.b64encode(f"anystring:{token}".encode()).decode()
            resp = get(endpoint, headers={"Authorization": f"Basic {auth}"}, raise_for_status=False)
        if resp.status_code == 200:
            data = resp.json() if resp.content else {}
            health = data.get("health_status", "OK")
            results.append(
                CheckResult(
                    name="validity",
                    status=CheckStatus.OK,
                    message=f"Token valid ({health})",
                    details={},
                    endpoint_used=endpoint,
                )
            )
        elif resp.status_code in (401, 403):
            results.append(
                CheckResult(
                    name="validity",
                    status=CheckStatus.ERROR,
                    message="Token invalid or expired. Check API key and dc (datacenter) if needed.",
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
        events.extend(safe_fetch_feed(url, "mailchimp", since=since))
    return events


def collect_status() -> None:
    return None


plugin = type("MailchimpPlugin", (), {
    "metadata": metadata,
    "token_checks": lambda self, token, config: token_checks(token, config),
    "collect_changes": lambda self, since: collect_changes(since),
    "collect_status": lambda self: collect_status(),
})()
