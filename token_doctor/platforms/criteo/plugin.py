"""
Criteo plugin: Marketing API (OAuth or API token).

Declared endpoints and docs; validation skipped in MVP.
"""

from __future__ import annotations

from typing import Any

from token_doctor.core.schema import CheckResult, CheckStatus, NormalizedEvent

DECLARED_ENDPOINTS: list[str] = []
CHANGELOG_FEEDS: list[str] = []
DOCS_LINKS = [
    "https://developers.criteo.com/",
    "https://developers.criteo.com/marketing-api",
]

metadata = {
    "platform": "criteo",
    "auth_types": ["oauth2", "api_token"],
    "documentation_links": DOCS_LINKS,
    "declared_endpoints": DECLARED_ENDPOINTS,
    "sources_monitored": CHANGELOG_FEEDS,
    "data_collected": ["No validation endpoint in MVP; see Criteo developer portal"],
}


def token_checks(token: str, config: Any) -> list[CheckResult]:
    """No standard /me in MVP."""
    results: list[CheckResult] = []
    results.append(
        CheckResult(
            name="validity",
            status=CheckStatus.SKIPPED,
            message="Criteo token validation not implemented in MVP; use Criteo developer portal.",
            endpoint_used="",
        )
    )
    return results


def collect_changes(since: Any) -> list[NormalizedEvent]:
    return []


def collect_status() -> None:
    return None


plugin = type("CriteoPlugin", (), {
    "metadata": metadata,
    "token_checks": lambda self, token, config: token_checks(token, config),
    "collect_changes": lambda self, since: collect_changes(since),
    "collect_status": lambda self: collect_status(),
})()
