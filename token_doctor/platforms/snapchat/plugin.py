"""
Snapchat plugin: token check via Business API (organizations or me).

OAuth 2.0 for Snapchat Marketing API; declared endpoints.
"""

from __future__ import annotations

from typing import Any

from token_doctor.core.http_client import get
from token_doctor.core.schema import CheckResult, CheckStatus, NormalizedEvent

DECLARED_ENDPOINTS = [
    "https://businessapi.snapchat.com/v1/me",
    "https://businessapi.snapchat.com/v1/organizations",
]
CHANGELOG_FEEDS: list[str] = []
DOCS_LINKS = [
    "https://marketingapi.snapchat.com/docs/",
    "https://businesshelp.snapchat.com/",
]

metadata = {
    "platform": "snapchat",
    "auth_types": ["oauth2"],
    "documentation_links": DOCS_LINKS,
    "declared_endpoints": DECLARED_ENDPOINTS,
    "sources_monitored": CHANGELOG_FEEDS,
    "data_collected": ["me or organizations for validation"],
}


def token_checks(token: str, config: Any) -> list[CheckResult]:
    """Validate token via Snapchat Business API /v1/me (Bearer)."""
    results: list[CheckResult] = []
    endpoint = "https://businessapi.snapchat.com/v1/me"
    try:
        resp = get(endpoint, token=token, raise_for_status=False)
        if resp.status_code == 200:
            data = resp.json() if resp.content else {}
            results.append(
                CheckResult(
                    name="validity",
                    status=CheckStatus.OK,
                    message="Token valid",
                    details={"id": data.get("id")},
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


plugin = type("SnapchatPlugin", (), {
    "metadata": metadata,
    "token_checks": lambda self, token, config: token_checks(token, config),
    "collect_changes": lambda self, since: collect_changes(since),
    "collect_status": lambda self: collect_status(),
})()
