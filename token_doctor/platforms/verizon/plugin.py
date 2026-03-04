"""
Verizon plugin: token check via Verizon Media / Yahoo APIs where applicable.

Verizon Media (now part of Yahoo) and Verizon Ads APIs; declared endpoints for transparency.
"""

from __future__ import annotations

from typing import Any

from token_doctor.core.schema import CheckResult, CheckStatus, NormalizedEvent

DECLARED_ENDPOINTS: list[str] = []
CHANGELOG_FEEDS: list[str] = []
DOCS_LINKS = [
    "https://developer.verizon.com/",
    "https://www.verizon.com/business/",
]

metadata = {
    "platform": "verizon",
    "auth_types": ["oauth2", "api_key"],
    "documentation_links": DOCS_LINKS,
    "declared_endpoints": DECLARED_ENDPOINTS,
    "sources_monitored": CHANGELOG_FEEDS,
    "data_collected": ["No validation endpoint in MVP; see docs for API access"],
}


def token_checks(token: str, config: Any) -> list[CheckResult]:
    """No standard /me endpoint; skip with message."""
    results: list[CheckResult] = []
    results.append(
        CheckResult(
            name="validity",
            status=CheckStatus.SKIPPED,
            message="Verizon token validation not implemented in MVP; use docs for API access.",
            endpoint_used="",
        )
    )
    return results


def collect_changes(since: Any) -> list[NormalizedEvent]:
    return []


def collect_status() -> None:
    return None


plugin = type("VerizonPlugin", (), {
    "metadata": metadata,
    "token_checks": lambda self, token, config: token_checks(token, config),
    "collect_changes": lambda self, since: collect_changes(since),
    "collect_status": lambda self: collect_status(),
})()
