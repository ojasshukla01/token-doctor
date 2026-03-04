"""Meta Marketing API plugin: changelog and version sunset tracking."""

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

# Declared sources (no token validation endpoint declared for Meta Marketing in MVP)
DECLARED_ENDPOINTS = ["https://graph.facebook.com/v21.0/me"]
CHANGELOG_FEEDS = [
    "https://developers.facebook.com/blog/feed/",
]
DOCS_LINKS = [
    "https://developers.facebook.com/docs/marketing-api",
]

metadata = {
    "platform": "meta_marketing",
    "auth_types": ["oauth", "system_user"],
    "documentation_links": DOCS_LINKS,
    "declared_endpoints": DECLARED_ENDPOINTS,
    "sources_monitored": CHANGELOG_FEEDS,
    "data_collected": ["changelog entries from RSS; version/sunset keywords"],
}


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


def token_checks(token: str, config: Any) -> list[CheckResult]:
    """Meta Marketing API token check (optional: validate via graph API)."""
    results: list[CheckResult] = []
    # Meta Graph API me endpoint - declared if we use it
    endpoint = "https://graph.facebook.com/v21.0/me?fields=id,name"
    try:
        resp = get("https://graph.facebook.com/v21.0/me", token=token)
        if resp.status_code == 200:
            data = resp.json()
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
        elif resp.status_code == 401:
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
                    message=f"Status {resp.status_code}",
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


def collect_changes(since: datetime | None) -> list[NormalizedEvent]:
    """Fetch Meta developer blog feed and normalize events."""
    events: list[NormalizedEvent] = []
    for feed_url in CHANGELOG_FEEDS:
        try:
            resp = get(feed_url)
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
                if any(k in title.lower() for k in ("deprecat", "sunset", "version", "upgrade", "marketing api")):
                    event_type = EventType.DEPRECATION if "deprecat" in title.lower() or "sunset" in title.lower() else EventType.VERSION_UPGRADE
                events.append(
                    NormalizedEvent(
                        platform="meta_marketing",
                        event_type=event_type,
                        title=title,
                        description=summary or "",
                        url=link or None,
                        published_at=published,
                        effective_date=published,
                        confidence=ConfidenceLevel.MEDIUM,
                        source_type="rss",
                        raw_id=entry.get("id", link or title)[:200],
                        metadata={},
                    )
                )
        except Exception:
            continue
    return events


def collect_status() -> list[NormalizedEvent] | None:
    return None


plugin = type("MetaMarketingPlugin", (), {
    "metadata": metadata,
    "token_checks": lambda self, token, config: token_checks(token, config),
    "collect_changes": lambda self, since: collect_changes(since),
    "collect_status": lambda self: collect_status(),
})()
