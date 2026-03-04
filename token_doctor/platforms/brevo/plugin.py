"""
Brevo plugin: token check via /account (API key in header api-key).

Brevo (Sendinblue) REST API; declared endpoints and docs.
"""

from __future__ import annotations

from typing import Any

from token_doctor.core.http_client import get
from token_doctor.core.schema import CheckResult, CheckStatus, NormalizedEvent

DECLARED_ENDPOINTS = ["https://api.brevo.com/v3/account"]
CHANGELOG_FEEDS: list[str] = []
DOCS_LINKS = [
    "https://developers.brevo.com/",
    "https://developers.brevo.com/changelog",
]

metadata = {
    "platform": "brevo",
    "auth_types": ["api_key"],
    "documentation_links": DOCS_LINKS,
    "declared_endpoints": DECLARED_ENDPOINTS,
    "sources_monitored": CHANGELOG_FEEDS,
    "data_collected": ["account info for validation"],
}


def token_checks(token: str, config: Any) -> list[CheckResult]:
    """Validate Brevo API key via GET /v3/account (api-key header)."""
    results: list[CheckResult] = []
    endpoint = "https://api.brevo.com/v3/account"
    try:
        resp = get(endpoint, headers={"api-key": token}, raise_for_status=False)
        if resp.status_code == 200:
            data = resp.json() if resp.content else {}
            email = data.get("email", "?")
            results.append(
                CheckResult(
                    name="validity",
                    status=CheckStatus.OK,
                    message=f"Token valid (account: {email})",
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


plugin = type("BrevoPlugin", (), {
    "metadata": metadata,
    "token_checks": lambda self, token, config: token_checks(token, config),
    "collect_changes": lambda self, since: collect_changes(since),
    "collect_status": lambda self: collect_status(),
})()
