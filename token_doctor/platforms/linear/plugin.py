"""Linear plugin: token check via GraphQL viewer, changelog from blog."""

from __future__ import annotations

from typing import Any

from token_doctor.core.http_client import post
from token_doctor.core.schema import CheckResult, CheckStatus, NormalizedEvent
from token_doctor.platforms.base import safe_fetch_feed

DECLARED_ENDPOINTS = ["https://api.linear.app/graphql"]
CHANGELOG_FEEDS = [
    "https://linear.app/blog/feed",
]
DOCS_LINKS = ["https://developers.linear.app/docs/graphql/working-with-the-graphql-api", "https://linear.app/blog"]

metadata = {
    "platform": "linear",
    "auth_types": ["api_key", "oauth"],
    "documentation_links": DOCS_LINKS,
    "declared_endpoints": DECLARED_ENDPOINTS,
    "sources_monitored": CHANGELOG_FEEDS,
    "data_collected": ["viewer id, name from GraphQL", "blog feed entries"],
}


def token_checks(token: str, config: Any) -> list[CheckResult]:
    """Validate API key via Linear GraphQL viewer query (Bearer)."""
    results: list[CheckResult] = []
    endpoint = "https://api.linear.app/graphql"
    try:
        resp = post(
            endpoint,
            token=token,
            json={"query": "query { viewer { id name email } }"},
            raise_for_status=False,
        )
        if resp.status_code == 200:
            data = resp.json() if resp.content else {}
            errors = data.get("errors", [])
            if errors:
                msg = errors[0].get("message", "GraphQL error")
                results.append(
                    CheckResult(
                        name="validity",
                        status=CheckStatus.ERROR,
                        message=msg[:200],
                        endpoint_used=endpoint,
                    )
                )
            else:
                viewer = (data.get("data") or {}).get("viewer") or {}
                name = viewer.get("name", viewer.get("email", "?"))
                results.append(
                    CheckResult(
                        name="validity",
                        status=CheckStatus.OK,
                        message=f"Token valid (user: {name})",
                        details={"id": viewer.get("id")},
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
    events: list[NormalizedEvent] = []
    for url in CHANGELOG_FEEDS:
        events.extend(safe_fetch_feed(url, "linear", since=since))
    return events


def collect_status() -> None:
    return None


plugin = type("LinearPlugin", (), {
    "metadata": metadata,
    "token_checks": lambda self, token, config: token_checks(token, config),
    "collect_changes": lambda self, since: collect_changes(since),
    "collect_status": lambda self: collect_status(),
})()
