"""Notion plugin: token check via /users/me, changelog from updates page."""

from __future__ import annotations

from typing import Any

from token_doctor.core.http_client import get
from token_doctor.core.schema import CheckResult, CheckStatus, NormalizedEvent

DECLARED_ENDPOINTS = ["https://api.notion.com/v1/users/me"]
CHANGELOG_FEEDS: list[str] = []  # Notion doesn't publish a public API changelog RSS
DOCS_LINKS = ["https://developers.notion.com/", "https://www.notion.so/notion/What-s-New-157765353f2c4705bd45474e5ba8b46c"]

metadata = {
    "platform": "notion",
    "auth_types": ["oauth", "internal_integration"],
    "documentation_links": DOCS_LINKS,
    "declared_endpoints": DECLARED_ENDPOINTS,
    "sources_monitored": [],
    "data_collected": ["user id from /users/me"],
}


def token_checks(token: str, config: Any) -> list[CheckResult]:
    """Validate token via Notion /v1/users/me (Bearer, Notion-Version header)."""
    results: list[CheckResult] = []
    endpoint = "https://api.notion.com/v1/users/me"
    try:
        resp = get(
            endpoint,
            token=token,
            headers={"Notion-Version": "2022-06-28"},
            raise_for_status=False,
        )
        if resp.status_code == 200:
            data = resp.json() if resp.content else {}
            name = data.get("name", "?")
            results.append(
                CheckResult(
                    name="validity",
                    status=CheckStatus.OK,
                    message=f"Token valid (user: {name})",
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


plugin = type("NotionPlugin", (), {
    "metadata": metadata,
    "token_checks": lambda self, token, config: token_checks(token, config),
    "collect_changes": lambda self, since: collect_changes(since),
    "collect_status": lambda self: collect_status(),
})()
