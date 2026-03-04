"""
Yahoo plugin: token check via Yahoo Ads (formerly Gemini) API.

OAuth 2.0; account or user endpoint for validation. Declared endpoints and docs.
"""

from __future__ import annotations

from typing import Any

from token_doctor.core.http_client import get
from token_doctor.core.schema import CheckResult, CheckStatus, NormalizedEvent

# Yahoo Advertising (ads.yahoo.com) API
DECLARED_ENDPOINTS = [
    "https://api.admanager.yahoo.com/v3/rest/account",
    "https://api.admanager.yahoo.com/v3/rest/reports/metadata",
]
CHANGELOG_FEEDS: list[str] = []
DOCS_LINKS = [
    "https://developer.yahoo.com/",
    "https://developer.yahoo.com/ads/api/",
]

metadata = {
    "platform": "yahoo",
    "auth_types": ["oauth2"],
    "documentation_links": DOCS_LINKS,
    "declared_endpoints": DECLARED_ENDPOINTS,
    "sources_monitored": CHANGELOG_FEEDS,
    "data_collected": ["account or report metadata for validation"],
}


def token_checks(token: str, config: Any) -> list[CheckResult]:
    """Validate token via Yahoo Ads API account or metadata endpoint (Bearer)."""
    results: list[CheckResult] = []
    endpoint = "https://api.admanager.yahoo.com/v3/rest/reports/metadata"
    try:
        resp = get(endpoint, token=token, raise_for_status=False)
        if resp.status_code == 200:
            results.append(
                CheckResult(
                    name="validity",
                    status=CheckStatus.OK,
                    message="Token valid",
                    details={},
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
    return []


def collect_status() -> None:
    return None


plugin = type("YahooPlugin", (), {
    "metadata": metadata,
    "token_checks": lambda self, token, config: token_checks(token, config),
    "collect_changes": lambda self, since: collect_changes(since),
    "collect_status": lambda self: collect_status(),
})()
