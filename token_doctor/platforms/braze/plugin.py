"""
Braze plugin: token check via /users/export/ids or /dashboard (REST API key).

Uses Bearer API key; endpoint may require app group or similar. Declared endpoints for transparency.
"""

from __future__ import annotations

from typing import Any

from token_doctor.core.http_client import get
from token_doctor.core.schema import CheckResult, CheckStatus, NormalizedEvent

# Braze REST API base is region-specific: https://rest.iad-01.braze.com or api.braze.com
DECLARED_ENDPOINTS = [
    "https://rest.iad-01.braze.com/dashboard/data_export",
    "https://rest.iad-01.braze.com/users/export/ids",
]
CHANGELOG_FEEDS: list[str] = []
DOCS_LINKS = [
    "https://www.braze.com/docs/api/basics/",
    "https://www.braze.com/docs/developer_platform/",
]

metadata = {
    "platform": "braze",
    "auth_types": ["api_key", "rest_api_key"],
    "documentation_links": DOCS_LINKS,
    "declared_endpoints": DECLARED_ENDPOINTS,
    "sources_monitored": CHANGELOG_FEEDS,
    "data_collected": ["export/dashboard endpoint for validation"],
}


def _get_rest_url(config: Any) -> str:
    """Braze REST base URL; can be overridden via profile option 'rest_url' (e.g. https://rest.iad-01.braze.com)."""
    if config and getattr(config, "get_profile", None):
        profile = config.get_profile("braze")
        if profile and profile.options.get("rest_url"):
            raw = profile.options["rest_url"]
            return str(raw).rstrip("/") if raw else "https://rest.iad-01.braze.com"
    return "https://rest.iad-01.braze.com"


def token_checks(token: str, config: Any) -> list[CheckResult]:
    """Validate Braze REST API key via dashboard/data_export (Bearer)."""
    results: list[CheckResult] = []
    base = _get_rest_url(config)
    endpoint = f"{base}/dashboard/data_export"
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


plugin = type("BrazePlugin", (), {
    "metadata": metadata,
    "token_checks": lambda self, token, config: token_checks(token, config),
    "collect_changes": lambda self, since: collect_changes(since),
    "collect_status": lambda self: collect_status(),
})()
