"""
Base utilities for platform plugins.

- Safe HTTP fetch that catches API/network errors and returns None or empty list.
- Common feed parsing (RSS/Atom) with date handling.
- No token is ever logged or included in errors.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import feedparser  # type: ignore[import-untyped]

from token_doctor.core.exceptions import APIError, AuthenticationError, NetworkError
from token_doctor.core.http_client import get
from token_doctor.core.schema import (
    ConfidenceLevel,
    EventType,
    NormalizedEvent,
)


def _parse_feed_date(entry: Any) -> datetime | None:
    """Extract published or updated datetime from feed entry."""
    for key in ("published_parsed", "updated_parsed"):
        val = getattr(entry, key, None)
        if val and len(val) >= 6:
            try:
                from time import struct_time
                if isinstance(val, struct_time):
                    return datetime(*val[:6])
            except (TypeError, ValueError):
                pass
    return None


def parse_feed_entries(
    content: bytes | str,
    platform: str,
    source_type: str = "rss",
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM,
    since: datetime | None = None,
    event_type_hint: EventType = EventType.ANNOUNCEMENT,
) -> list[NormalizedEvent]:
    """
    Parse RSS/Atom content into NormalizedEvents.
    Filters by `since` if provided.
    """
    events: list[NormalizedEvent] = []
    try:
        fp = feedparser.parse(content)
    except Exception:
        return events
    for entry in getattr(fp, "entries", []):
        title = entry.get("title") or ""
        if not title:
            continue
        link = entry.get("link") or ""
        summary = entry.get("summary") or ""
        published = _parse_feed_date(entry)
        if since and published and published < since:
            continue
        raw_id = (entry.get("id") or link or title)[:200]
        # Infer event type from title keywords
        tl = title.lower()
        if any(k in tl for k in ("deprecat", "sunset", "end of life", "eol")):
            ev_type = EventType.DEPRECATION
        elif "maintenance" in tl:
            ev_type = EventType.MAINTENANCE
        elif any(k in tl for k in ("version", "release", "upgrade")):
            ev_type = EventType.VERSION_UPGRADE
        else:
            ev_type = event_type_hint
        events.append(
            NormalizedEvent(
                platform=platform,
                event_type=ev_type,
                title=title,
                description=summary,
                url=link or None,
                published_at=published,
                effective_date=published,
                confidence=confidence,
                source_type=source_type,
                raw_id=raw_id,
                metadata={},
            )
        )
    return events


def safe_fetch_feed(
    url: str,
    platform: str,
    since: datetime | None = None,
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM,
    timeout: float = 25.0,
) -> list[NormalizedEvent]:
    """
    Fetch URL (no auth), parse as RSS/Atom, return normalized events.
    On any network/API error, returns empty list (no exception).
    """
    try:
        response = get(url, timeout=timeout, raise_for_status=False)
    except (NetworkError, APIError, AuthenticationError):
        return []
    if response.status_code != 200:
        return []
    return parse_feed_entries(
        response.content,
        platform=platform,
        source_type="rss",
        confidence=confidence,
        since=since,
    )


def safe_get(
    url: str,
    token: str | None = None,
    timeout: float = 25.0,
    raise_for_status: bool = False,
) -> Any:
    """
    GET URL with optional Bearer token.
    If raise_for_status is False, returns response anyway (caller checks .status_code).
    If True, raises token_doctor exceptions on 4xx/5xx.
    """
    return get(
        url,
        token=token,
        timeout=timeout,
        raise_for_status=raise_for_status,
    )
