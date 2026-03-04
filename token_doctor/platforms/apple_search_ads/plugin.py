"""
Apple Search Ads plugin: token check via API (JWT or auth header).

ASA API uses JWT or client credentials; declared endpoints for transparency.
"""

from __future__ import annotations

from typing import Any

from token_doctor.core.http_client import get
from token_doctor.core.schema import CheckResult, CheckStatus, NormalizedEvent

DECLARED_ENDPOINTS = [
    "https://api.searchads.apple.com/api/v5/acls",
    "https://api.searchads.apple.com/api/v5/campaigns",
]
CHANGELOG_FEEDS: list[str] = []
DOCS_LINKS = [
    "https://developer.apple.com/documentation/apple_search_ads_api",
    "https://searchads.apple.com/",
]

metadata = {
    "platform": "apple_search_ads",
    "auth_types": ["jwt", "client_credentials"],
    "documentation_links": DOCS_LINKS,
    "declared_endpoints": DECLARED_ENDPOINTS,
    "sources_monitored": CHANGELOG_FEEDS,
    "data_collected": ["acls or campaigns for validation"],
}


def token_checks(token: str, config: Any) -> list[CheckResult]:
    """Validate Apple Search Ads token via GET /api/v5/acls (Bearer JWT)."""
    results: list[CheckResult] = []
    endpoint = "https://api.searchads.apple.com/api/v5/acls"
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


plugin = type("AppleSearchAdsPlugin", (), {
    "metadata": metadata,
    "token_checks": lambda self, token, config: token_checks(token, config),
    "collect_changes": lambda self, since: collect_changes(since),
    "collect_status": lambda self: collect_status(),
})()
