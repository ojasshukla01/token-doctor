"""
Alert thresholds and helpers for token expiry and sunset/deprecation.

Alerts are raised at 30, 15, 7, and 1 day(s) before expiry or sunset.
Profile option "api_version" (or "version") can be set so sunset alerts
only match events relevant to the version the user is using.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Alert user at these days before expiry/sunset
ALERT_DAYS = (30, 15, 7, 1)


@dataclass
class TokenExpiryAlert:
    platform: str
    expires_at: datetime
    days_until: int


@dataclass
class SunsetAlert:
    platform: str
    title: str
    effective_date: datetime
    days_until: int
    event_type: str
    url: str | None
    user_version_matched: bool  # True if profile has api_version and event matches it


def get_token_expiry_alerts(
    config: Any,
    within_days: int = 30,
) -> list[TokenExpiryAlert]:
    """Return token expiry alerts for profiles where JWT expires within within_days and days_until is in ALERT_DAYS."""
    from token_doctor.core.jwt_utils import get_jwt_expiry
    from token_doctor.core.secrets import get_token

    now = datetime.now(timezone.utc)
    out: list[TokenExpiryAlert] = []
    for p in config.profiles:
        if not p.enabled:
            continue
        tok = get_token(p.platform, config.config_dir)
        if not tok:
            continue
        exp = get_jwt_expiry(tok)
        if not exp:
            continue
        delta = (exp - now).days
        if delta < 0:
            delta = 0  # already expired
        if delta <= within_days and delta in ALERT_DAYS:
            out.append(TokenExpiryAlert(platform=p.platform, expires_at=exp, days_until=delta))
    return out


def get_sunset_alerts(
    config: Any,
    db_path: Path,
    within_days: int = 30,
) -> list[SunsetAlert]:
    """Return sunset/deprecation alerts for events within within_days where days_until is in ALERT_DAYS.

    If a profile has options.api_version or options.version, only include events
    whose title or description contains that version string (so user sees alerts
    relevant to their version).
    """
    from token_doctor.core.cache import get_next_deadlines
    from token_doctor.core.schema import EventType

    now = datetime.now(timezone.utc)
    deadlines = get_next_deadlines(db_path, limit=100)
    out: list[SunsetAlert] = []
    for ev in deadlines:
        if ev.event_type not in (EventType.SUNSET, EventType.DEPRECATION):
            continue
        if not ev.effective_date:
            continue
        delta = (ev.effective_date - now).days
        if delta < 0:
            continue
        if delta > within_days:
            continue
        if delta not in ALERT_DAYS:
            continue
        profile = config.get_profile(ev.platform)
        user_version: str | None = None
        if profile and profile.options:
            user_version = profile.options.get("api_version") or profile.options.get("version")
        user_version_matched = True
        if user_version:
            uv = user_version.lower()
            title_lower = (ev.title or "").lower()
            desc_lower = (ev.description or "").lower()
            user_version_matched = uv in title_lower or uv in desc_lower
        else:
            user_version_matched = True
        if not user_version_matched:
            continue  # User set a version but this event doesn't match it; skip
        out.append(
            SunsetAlert(
                platform=ev.platform,
                title=ev.title,
                effective_date=ev.effective_date,
                days_until=delta,
                event_type=ev.event_type.value,
                url=ev.url,
                user_version_matched=user_version_matched,
            )
        )
    return out
