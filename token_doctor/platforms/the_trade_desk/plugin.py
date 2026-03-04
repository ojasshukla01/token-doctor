"""
The Trade Desk plugin: token/API access for advertiser and campaign APIs.

Declared endpoints and docs; validation via identity or advertiser list if available.
"""

from __future__ import annotations

from typing import Any

from token_doctor.core.schema import CheckResult, CheckStatus, NormalizedEvent

DECLARED_ENDPOINTS: list[str] = []
CHANGELOG_FEEDS: list[str] = []
DOCS_LINKS = [
    "https://partner.thetradedesk.com/v3/portal/api/doc",
    "https://www.thetradedesk.com/",
]

metadata = {
    "platform": "the_trade_desk",
    "auth_types": ["api_key", "oauth2"],
    "documentation_links": DOCS_LINKS,
    "declared_endpoints": DECLARED_ENDPOINTS,
    "sources_monitored": CHANGELOG_FEEDS,
    "data_collected": ["No validation endpoint in MVP; see TTD portal API docs"],
}


def token_checks(token: str, config: Any) -> list[CheckResult]:
    """No standard /me in MVP."""
    results: list[CheckResult] = []
    results.append(
        CheckResult(
            name="validity",
            status=CheckStatus.SKIPPED,
            message="The Trade Desk token validation not implemented in MVP; use TTD portal API docs.",
            endpoint_used="",
        )
    )
    return results


def collect_changes(since: Any) -> list[NormalizedEvent]:
    return []


def collect_status() -> None:
    return None


plugin = type("TheTradeDeskPlugin", (), {
    "metadata": metadata,
    "token_checks": lambda self, token, config: token_checks(token, config),
    "collect_changes": lambda self, since: collect_changes(since),
    "collect_status": lambda self: collect_status(),
})()
