"""Generate ICS calendar events for sunsets, deadlines, maintenance, token expiry."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import cast
from uuid import uuid4

from icalendar import Calendar, Event  # type: ignore[import-untyped]

from token_doctor.core.schema import NormalizedEvent, PlatformReport


def _add_event(
    cal: Calendar,
    summary: str,
    dt: datetime,
    description: str = "",
    url: str | None = None,
    uid: str | None = None,
) -> None:
    e = Event()
    e.add("uid", uid or str(uuid4()))
    e.add("dtstamp", datetime.now(timezone.utc))
    e.add("dtstart", dt.date() if hasattr(dt, "date") else dt)
    e.add("summary", summary)
    if description:
        e.add("description", description)
    if url:
        e.add("url", url)
    cal.add_component(e)


def events_to_ics(events: list[NormalizedEvent], title: str = "token-doctor") -> bytes:
    """Build ICS calendar from normalized events (sunset, deprecation, maintenance)."""
    cal = Calendar()
    cal.add("prodid", f"-//token-doctor//{title}//EN")
    cal.add("version", "2.0")
    cal.add("x-wr-calname", title)
    for ev in events:
        dt = ev.effective_date or ev.published_at
        if not dt:
            continue
        summary = f"[{ev.platform}] {ev.title}"
        desc = ev.description[:500] if ev.description else ""
        if ev.url:
            desc = (desc + "\n" + ev.url) if desc else ev.url
        _add_event(cal, summary, dt, desc, ev.url, uid=f"td-{ev.platform}-{ev.raw_id}")
    return cast(bytes, cal.to_ical())


def report_to_ics(report: PlatformReport, include_token_expiry: bool = True) -> bytes:
    """Build ICS from a platform report (events + optional token expiry)."""
    events = report.events
    cal = Calendar()
    cal.add("prodid", f"-//token-doctor//{report.platform}//EN")
    cal.add("version", "2.0")
    cal.add("x-wr-calname", f"token-doctor: {report.platform}")
    for ev in events:
        dt = ev.effective_date or ev.published_at
        if not dt:
            continue
        summary = f"[{ev.platform}] {ev.title}"
        desc = ev.description[:500] if ev.description else ""
        if ev.url:
            desc = (desc + "\n" + ev.url) if desc else ev.url
        _add_event(cal, summary, dt, desc, ev.url, uid=f"td-{ev.platform}-{ev.raw_id}")
    if include_token_expiry:
        expiry = report.token_metadata.get("expires_at")
        if isinstance(expiry, datetime):
            _add_event(
                cal,
                f"[{report.platform}] Token expiration",
                expiry,
                "Token expiration (from JWT or plugin)",
                uid=f"td-{report.platform}-token-expiry",
            )
        elif isinstance(expiry, str):
            try:
                dt = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
                _add_event(
                    cal,
                    f"[{report.platform}] Token expiration",
                    dt,
                    "Token expiration (from JWT or plugin)",
                    uid=f"td-{report.platform}-token-expiry",
                )
            except ValueError:
                pass
    return cast(bytes, cal.to_ical())


def export_ics(
    reports: list[PlatformReport],
    output_path: Path,
    combined: bool = True,
) -> list[Path]:
    """Export ICS file(s). If combined, one file; else one per platform. Returns paths written."""
    written: list[Path] = []
    output_path = Path(output_path)
    if combined and reports:
        all_events: list[NormalizedEvent] = []
        for r in reports:
            all_events.extend(r.events)
        ics = events_to_ics(all_events, "token-doctor-all")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(ics)
        written.append(output_path)
    else:
        single_file = output_path.suffix.lower() == ".ics" and len(reports) == 1
        for r in reports:
            if single_file:
                p = output_path
            else:
                p = output_path.parent / f"{r.platform}.ics" if output_path.suffix.lower() == ".ics" else output_path / f"{r.platform}.ics"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(report_to_ics(r))
            written.append(p)
            if single_file:
                break
    return written
