"""
Segment plugin: workspace/sources API with token (Bearer).

Segment uses different auth for Config API (personas token) vs write keys; declared endpoints for transparency.
"""

from __future__ import annotations

from typing import Any

from token_doctor.core.http_client import get
from token_doctor.core.schema import CheckResult, CheckStatus, NormalizedEvent

DECLARED_ENDPOINTS = [
    "https://api.segmentapis.com/workspaces",
    "https://api.segmentapis.com/sources",
]
CHANGELOG_FEEDS: list[str] = []
DOCS_LINKS = [
    "https://segment.com/docs/connections/",
    "https://docs.segmentapis.com/",
]

metadata = {
    "platform": "segment",
    "auth_types": ["personas_token", "write_key", "api_token"],
    "documentation_links": DOCS_LINKS,
    "declared_endpoints": DECLARED_ENDPOINTS,
    "sources_monitored": CHANGELOG_FEEDS,
    "data_collected": ["workspaces or sources list for validation"],
}


def token_checks(token: str, config: Any) -> list[CheckResult]:
    """Validate Segment API token via GET workspaces (Bearer)."""
    results: list[CheckResult] = []
    endpoint = "https://api.segmentapis.com/workspaces"
    try:
        resp = get(endpoint, token=token, raise_for_status=False)
        if resp.status_code == 200:
            data = resp.json() if resp.content else {}
            workspaces = data.get("data", data) if isinstance(data, dict) else []
            count = len(workspaces) if isinstance(workspaces, list) else 0
            results.append(
                CheckResult(
                    name="validity",
                    status=CheckStatus.OK,
                    message=f"Token valid ({count} workspace(s))",
                    details={"count": count},
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


plugin = type("SegmentPlugin", (), {
    "metadata": metadata,
    "token_checks": lambda self, token, config: token_checks(token, config),
    "collect_changes": lambda self, since: collect_changes(since),
    "collect_status": lambda self: collect_status(),
})()
