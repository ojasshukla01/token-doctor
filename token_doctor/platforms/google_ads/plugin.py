"""Google Ads API plugin: release notes and version lifecycle."""

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

DECLARED_ENDPOINTS: list[str] = []
# Google Ads API release notes RSS if available; fallback to blog
CHANGELOG_FEEDS = [
    "https://developers.google.com/google-ads/api/docs/release-notes/feed",
    "https://ads-developers.googleblog.com/feeds/posts/default",
]
DOCS_LINKS = [
    "https://developers.google.com/google-ads/api/docs/start",
]

metadata = {
    "platform": "google_ads",
    "auth_types": ["oauth2", "service_account"],
    "documentation_links": DOCS_LINKS,
    "declared_endpoints": DECLARED_ENDPOINTS,
    "sources_monitored": CHANGELOG_FEEDS,
    "data_collected": ["release notes and blog entries; version/sunset keywords"],
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
    """Google Ads does not expose a simple /me; skip or minimal check."""
    results: list[CheckResult] = []
    results.append(
        CheckResult(
            name="validity",
            status=CheckStatus.SKIPPED,
            message="Google Ads token validation not implemented (no simple /me endpoint); use changes fetch only.",
            endpoint_used="",
        )
    )
    return results


def collect_changes(since: datetime | None) -> list[NormalizedEvent]:
    """Fetch Google Ads release notes / blog feeds."""
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
                tl = title.lower()
                if "deprecat" in tl or "sunset" in tl or "end of life" in tl:
                    event_type = EventType.DEPRECATION
                elif "version" in tl or "release" in tl:
                    event_type = EventType.VERSION_UPGRADE
                events.append(
                    NormalizedEvent(
                        platform="google_ads",
                        event_type=event_type,
                        title=title,
                        description=summary or "",
                        url=link or None,
                        published_at=published,
                        effective_date=published,
                        confidence=ConfidenceLevel.HIGH if "release-notes" in feed_url else ConfidenceLevel.MEDIUM,
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


plugin = type("GoogleAdsPlugin", (), {
    "metadata": metadata,
    "token_checks": lambda self, token, config: token_checks(token, config),
    "collect_changes": lambda self, since: collect_changes(since),
    "collect_status": lambda self: collect_status(),
})()
