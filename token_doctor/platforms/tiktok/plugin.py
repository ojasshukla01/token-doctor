"""
TikTok plugin: token check via Business API user/info or advertiser list.

OAuth 2.0 for TikTok for Business; declared endpoints and developer resources.
"""

from __future__ import annotations

from typing import Any

from token_doctor.core.http_client import get
from token_doctor.core.schema import CheckResult, CheckStatus, NormalizedEvent

DECLARED_ENDPOINTS = [
    "https://business-api.tiktok.com/open_api/v1.3/user/info/",
    "https://business-api.tiktok.com/open_api/v1.3/advertiser/list/",
]
CHANGELOG_FEEDS: list[str] = []
DOCS_LINKS = [
    "https://business-api.tiktok.com/portal/docs",
    "https://developers.tiktok.com/",
]

metadata = {
    "platform": "tiktok",
    "auth_types": ["oauth2"],
    "documentation_links": DOCS_LINKS,
    "declared_endpoints": DECLARED_ENDPOINTS,
    "sources_monitored": CHANGELOG_FEEDS,
    "data_collected": ["user info or advertiser list for validation"],
}


def token_checks(token: str, config: Any) -> list[CheckResult]:
    """Validate token via TikTok Business API user/info (Bearer)."""
    results: list[CheckResult] = []
    endpoint = "https://business-api.tiktok.com/open_api/v1.3/user/info/"
    try:
        resp = get(endpoint, token=token, raise_for_status=False)
        if resp.status_code == 200:
            data = resp.json() if resp.content else {}
            if data.get("code") == 0:
                results.append(
                    CheckResult(
                        name="validity",
                        status=CheckStatus.OK,
                        message="Token valid",
                        details={},
                        endpoint_used=endpoint,
                    )
                )
            else:
                results.append(
                    CheckResult(
                        name="validity",
                        status=CheckStatus.ERROR,
                        message=data.get("message", "API error")[:200],
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


plugin = type("TikTokPlugin", (), {
    "metadata": metadata,
    "token_checks": lambda self, token, config: token_checks(token, config),
    "collect_changes": lambda self, since: collect_changes(since),
    "collect_status": lambda self: collect_status(),
})()
