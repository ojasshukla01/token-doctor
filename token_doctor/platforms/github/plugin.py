"""GitHub plugin: token check via /user, API changelog feeds."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import feedparser  # type: ignore[import-untyped]

from token_doctor.core.http_client import get
from token_doctor.core.schema import (
    CheckResult,
    CheckStatus,
    ConfidenceLevel,
    EventType,
    NormalizedEvent,
)

# Declared endpoints and sources (manifest)
DECLARED_ENDPOINTS = ["https://api.github.com/user"]
CHANGELOG_FEEDS = [
    "https://github.blog/changelog/feed/",
    "https://developer.github.com/changes/feed",  # legacy; may redirect
]
DOCS_LINKS = [
    "https://docs.github.com/en/rest",
    "https://developer.github.com/changes",
]

metadata = {
    "platform": "github",
    "auth_types": ["oauth", "pat", "app"],
    "documentation_links": DOCS_LINKS,
    "declared_endpoints": DECLARED_ENDPOINTS,
    "sources_monitored": CHANGELOG_FEEDS,
    "data_collected": ["user id, login, scopes (from /user)", "changelog entries from RSS"],
}


def token_checks(token: str, config: Any) -> list[CheckResult]:
    """Validate token via GitHub /user endpoint."""
    results: list[CheckResult] = []
    endpoint = "https://api.github.com/user"
    try:
        resp = get(endpoint, token=token)
        if resp.status_code == 200:
            data = resp.json()
            login = data.get("login", "?")
            results.append(
                CheckResult(
                    name="validity",
                    status=CheckStatus.OK,
                    message=f"Token valid (user: {login})",
                    details={"login": login, "id": data.get("id")},
                    endpoint_used=endpoint,
                )
            )
            # Scopes from header if present
            scopes = resp.headers.get("X-OAuth-Scopes")
            if scopes:
                results.append(
                    CheckResult(
                        name="scopes",
                        status=CheckStatus.OK,
                        message=f"Scopes: {scopes}",
                        details={"scopes": scopes.strip().split(", ") if scopes else []},
                        endpoint_used=endpoint,
                    )
                )
        elif resp.status_code == 401:
            results.append(
                CheckResult(
                    name="validity",
                    status=CheckStatus.ERROR,
                    message="Token invalid or expired",
                    endpoint_used=endpoint,
                )
            )
        elif resp.status_code == 403:
            results.append(
                CheckResult(
                    name="permissions",
                    status=CheckStatus.ERROR,
                    message="Forbidden (rate limit or insufficient scopes)",
                    details={"status_code": 403},
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


def _parse_date(entry: Any) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        val = getattr(entry, key, None)
        if val and len(val) >= 6:
            try:
                from time import struct_time
                if isinstance(val, struct_time):
                    return datetime(*val[:6])
            except Exception:
                pass
    return None


# Shorter timeout for public RSS feeds so we don't hang on slow/unresponsive URLs
FEED_TIMEOUT = 15.0


def collect_changes(since: datetime | None) -> list[NormalizedEvent]:
    """Fetch GitHub changelog feeds and return normalized events."""
    events: list[NormalizedEvent] = []
    for feed_url in CHANGELOG_FEEDS:
        try:
            resp = get(feed_url, timeout=FEED_TIMEOUT)
            if resp.status_code != 200:
                continue
            fp = feedparser.parse(resp.content)
            for entry in getattr(fp, "entries", []):
                title = entry.get("title", "")
                link = entry.get("link", "")
                summary = entry.get("summary", "")
                if not title:
                    continue
                published = _parse_date(entry)
                if since and published and published < since:
                    continue
                event_type = EventType.ANNOUNCEMENT
                effective = published
                if any(k in title.lower() for k in ("deprecat", "sunset", "end of life")):
                    event_type = EventType.DEPRECATION
                elif "maintenance" in title.lower():
                    event_type = EventType.MAINTENANCE
                events.append(
                    NormalizedEvent(
                        platform="github",
                        event_type=event_type,
                        title=title,
                        description=summary or "",
                        url=link or None,
                        published_at=published,
                        effective_date=effective,
                        confidence=ConfidenceLevel.HIGH,
                        source_type="rss",
                        raw_id=entry.get("id", link or title)[:200],
                        metadata={},
                    )
                )
        except Exception:
            continue
    return events


def collect_status() -> list[NormalizedEvent] | None:
    """Optional: GitHub status page events. Not implemented for MVP."""
    return None


plugin = type("GitHubPlugin", (), {
    "metadata": metadata,
    "token_checks": lambda self, token, config: token_checks(token, config),
    "collect_changes": lambda self, since: collect_changes(since),
    "collect_status": lambda self: collect_status(),
})()
