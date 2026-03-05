"""SQLite cache for change events, fetch timestamps, and event hashes."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from token_doctor.core.schema import NormalizedEvent


def _event_hash(event: NormalizedEvent) -> str:
    data = f"{event.platform}|{event.raw_id}|{event.title}|{event.event_type.value}"
    if event.effective_date:
        data += f"|{event.effective_date.isoformat()}"
    return hashlib.sha256(data.encode()).hexdigest()[:32]


def _event_to_row(event: NormalizedEvent) -> tuple[str | None, str, str, str | None, str, str, str, str, str, str, str, str]:
    return (
        event.platform,
        event.event_type.value,
        event.title,
        event.description,
        event.url or "",
        event.published_at.isoformat() if event.published_at else "",
        event.effective_date.isoformat() if event.effective_date else "",
        event.confidence.value,
        event.source_type,
        event.raw_id,
        json.dumps(event.metadata),
        _event_hash(event),
    )


def init_db(db_path: Path) -> None:
    """Create SQLite schema if not exists."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    import sqlite3

    conn = sqlite3.connect(db_path)
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS events (
                platform TEXT NOT NULL,
                event_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                url TEXT,
                published_at TEXT,
                effective_date TEXT,
                confidence TEXT NOT NULL,
                source_type TEXT NOT NULL,
                raw_id TEXT NOT NULL,
                metadata TEXT,
                event_hash TEXT NOT NULL,
                fetched_at TEXT NOT NULL,
                PRIMARY KEY (platform, raw_id)
            );
            CREATE INDEX IF NOT EXISTS idx_events_platform ON events(platform);
            CREATE INDEX IF NOT EXISTS idx_events_effective_date ON events(effective_date);
            CREATE INDEX IF NOT EXISTS idx_events_platform_effective_date ON events(platform, effective_date);
            CREATE TABLE IF NOT EXISTS fetch_meta (
                platform TEXT PRIMARY KEY,
                last_fetch_at TEXT NOT NULL
            );
        """)
        conn.commit()
    finally:
        conn.close()


def upsert_events(db_path: Path, events: list[NormalizedEvent]) -> int:
    """Insert or replace events; update fetch_meta. Returns count written."""
    import sqlite3

    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(db_path)
    written = 0
    try:
        cur = conn.cursor()
        for event in events:
            row = _event_to_row(event) + (now,)
            cur.execute(
                """
                INSERT OR REPLACE INTO events (
                    platform, event_type, title, description, url,
                    published_at, effective_date, confidence, source_type,
                    raw_id, metadata, event_hash, fetched_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                row,
            )
            written += 1
        platforms = {e.platform for e in events}
        for platform in platforms:
            cur.execute(
                "INSERT OR REPLACE INTO fetch_meta (platform, last_fetch_at) VALUES (?, ?)",
                (platform, now),
            )
        conn.commit()
    finally:
        conn.close()
    return written


def get_events(
    db_path: Path,
    platform: str | None = None,
    since: datetime | None = None,
) -> list[NormalizedEvent]:
    """Load normalized events from cache."""
    import sqlite3

    from token_doctor.core.schema import ConfidenceLevel, EventType

    conn = sqlite3.connect(db_path)
    try:
        q = "SELECT platform, event_type, title, description, url, published_at, effective_date, confidence, source_type, raw_id, metadata FROM events WHERE 1=1"
        params: list[object] = []
        if platform:
            q += " AND platform = ?"
            params.append(platform)
        if since:
            q += " AND fetched_at >= ?"
            params.append(since.isoformat())
        q += " ORDER BY effective_date ASC, published_at ASC"
        cur = conn.execute(q, params)
        rows = cur.fetchall()
    finally:
        conn.close()

    out: list[NormalizedEvent] = []
    for r in rows:
        out.append(
            NormalizedEvent(
                platform=r[0],
                event_type=EventType(r[1]),
                title=r[2],
                description=r[3] or "",
                url=r[4] or None,
                published_at=datetime.fromisoformat(r[5]) if r[5] else None,
                effective_date=datetime.fromisoformat(r[6]) if r[6] else None,
                confidence=ConfidenceLevel(r[7]),
                source_type=r[8],
                raw_id=r[9],
                metadata=json.loads(r[10]) if r[10] else {},
            )
        )
    return out


def get_last_fetch(db_path: Path, platform: str) -> datetime | None:
    """Return last fetch time for platform."""
    import sqlite3

    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT last_fetch_at FROM fetch_meta WHERE platform = ?", (platform,)
        ).fetchone()
        if row:
            return datetime.fromisoformat(row[0])
        return None
    finally:
        conn.close()


def get_event_counts(db_path: Path, platform: str | None = None) -> dict[str, int]:
    """Return event count per platform. If platform is set, return only that platform."""
    import sqlite3

    conn = sqlite3.connect(db_path)
    try:
        if platform:
            row = conn.execute(
                "SELECT COUNT(*) FROM events WHERE platform = ?", (platform,)
            ).fetchone()
            return {platform: row[0]} if row else {}
        cur = conn.execute(
            "SELECT platform, COUNT(*) FROM events GROUP BY platform"
        )
        return dict(cur.fetchall())
    finally:
        conn.close()


def get_next_deadlines(
    db_path: Path,
    platform: str | None = None,
    limit: int = 10,
) -> list[NormalizedEvent]:
    """Return events with effective_date in the future, ordered by effective_date ascending."""
    import sqlite3

    from token_doctor.core.schema import ConfidenceLevel, EventType

    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(db_path)
    try:
        q = """
            SELECT platform, event_type, title, description, url, published_at, effective_date,
                   confidence, source_type, raw_id, metadata
            FROM events WHERE effective_date >= ? AND effective_date IS NOT NULL AND effective_date != ''
        """
        params: list[object] = [now]
        if platform:
            q += " AND platform = ?"
            params.append(platform)
        q += " ORDER BY effective_date ASC LIMIT ?"
        params.append(limit)
        cur = conn.execute(q, params)
        rows = cur.fetchall()
    finally:
        conn.close()

    out: list[NormalizedEvent] = []
    for r in rows:
        out.append(
            NormalizedEvent(
                platform=r[0],
                event_type=EventType(r[1]),
                title=r[2],
                description=r[3] or "",
                url=r[4] or None,
                published_at=datetime.fromisoformat(r[5]) if r[5] else None,
                effective_date=datetime.fromisoformat(r[6]) if r[6] else None,
                confidence=ConfidenceLevel(r[7]),
                source_type=r[8],
                raw_id=r[9],
                metadata=json.loads(r[10]) if r[10] else {},
            )
        )
    return out
