"""
Acxiom plugin: declared endpoints and developer resources.

Acxiom APIs (data, identity, marketing) vary by product; no single public /me in MVP.
Token validation skipped with clear message; sources documented for transparency.
"""

from __future__ import annotations

from typing import Any

from token_doctor.core.schema import CheckResult, CheckStatus, NormalizedEvent

DECLARED_ENDPOINTS: list[str] = []
CHANGELOG_FEEDS: list[str] = []
DOCS_LINKS = [
    "https://www.acxiom.com/",
    "https://developer.acxiom.com/",
]

metadata = {
    "platform": "acxiom",
    "auth_types": ["api_key", "oauth2"],
    "documentation_links": DOCS_LINKS,
    "declared_endpoints": DECLARED_ENDPOINTS,
    "sources_monitored": CHANGELOG_FEEDS,
    "data_collected": ["No validation endpoint in MVP; see Acxiom developer portal"],
}


def token_checks(token: str, config: Any) -> list[CheckResult]:
    """No standard public /me; skip with message."""
    results: list[CheckResult] = []
    results.append(
        CheckResult(
            name="validity",
            status=CheckStatus.SKIPPED,
            message="Acxiom token validation not implemented in MVP; use Acxiom developer portal.",
            endpoint_used="",
        )
    )
    return results


def collect_changes(since: Any) -> list[NormalizedEvent]:
    return []


def collect_status() -> None:
    return None


plugin = type("AcxiomPlugin", (), {
    "metadata": metadata,
    "token_checks": lambda self, token, config: token_checks(token, config),
    "collect_changes": lambda self, since: collect_changes(since),
    "collect_status": lambda self: collect_status(),
})()
