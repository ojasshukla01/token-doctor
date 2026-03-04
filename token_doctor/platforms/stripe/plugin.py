"""Stripe plugin: secret key check via /v1/account, changelog from docs."""

from __future__ import annotations

from typing import Any

from token_doctor.core.http_client import get
from token_doctor.core.schema import CheckResult, CheckStatus, NormalizedEvent
from token_doctor.platforms.base import safe_fetch_feed

# Stripe uses Basic auth with secret key as username (password empty) or Bearer with sk_*
DECLARED_ENDPOINTS = ["https://api.stripe.com/v1/account"]
CHANGELOG_FEEDS: list[str] = []  # No public RSS; docs changelog is HTML
DOCS_LINKS = ["https://docs.stripe.com/changelog", "https://docs.stripe.com/api"]

metadata = {
    "platform": "stripe",
    "auth_types": ["secret_key", "publishable_key"],
    "documentation_links": DOCS_LINKS,
    "declared_endpoints": DECLARED_ENDPOINTS,
    "sources_monitored": ["https://docs.stripe.com/changelog"],
    "data_collected": ["account id from /v1/account", "changelog via docs URL"],
}


def token_checks(token: str, config: Any) -> list[CheckResult]:
    """Validate secret key via GET /v1/account (Stripe uses Bearer sk_*)."""
    results: list[CheckResult] = []
    endpoint = "https://api.stripe.com/v1/account"
    try:
        resp = get(endpoint, token=token, raise_for_status=False)
        if resp.status_code == 200:
            data = resp.json() if resp.content else {}
            acc_id = data.get("id", "?")
            results.append(
                CheckResult(
                    name="validity",
                    status=CheckStatus.OK,
                    message=f"Key valid (account: {acc_id})",
                    details={"account_id": acc_id},
                    endpoint_used=endpoint,
                )
            )
        elif resp.status_code in (401, 403):
            results.append(
                CheckResult(
                    name="validity",
                    status=CheckStatus.ERROR,
                    message="Invalid or unauthorized API key",
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
    events: list[NormalizedEvent] = []
    for url in CHANGELOG_FEEDS:
        events.extend(safe_fetch_feed(url, "stripe", since=since))
    return events


def collect_status() -> None:
    return None


plugin = type("StripePlugin", (), {
    "metadata": metadata,
    "token_checks": lambda self, token, config: token_checks(token, config),
    "collect_changes": lambda self, since: collect_changes(since),
    "collect_status": lambda self: collect_status(),
})()
