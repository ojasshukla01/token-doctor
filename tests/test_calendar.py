"""Tests for ICS calendar generation: deterministic and valid."""

from datetime import datetime

from token_doctor.core.calendar import events_to_ics, report_to_ics
from token_doctor.core.schema import (
    ConfidenceLevel,
    EventType,
    NormalizedEvent,
    PlatformReport,
)


def _sample_events():
    return [
        NormalizedEvent(
            platform="github",
            event_type=EventType.DEPRECATION,
            title="API v2 sunset",
            description="Please migrate.",
            url="https://example.com",
            published_at=datetime(2025, 6, 1),
            effective_date=datetime(2025, 12, 1),
            confidence=ConfidenceLevel.HIGH,
            source_type="rss",
            raw_id="evt-1",
            metadata={},
        ),
    ]


def test_events_to_ics_deterministic():
    events = _sample_events()
    ics1 = events_to_ics(events)
    ics2 = events_to_ics(events)
    assert ics1 == ics2
    assert b"VCALENDAR" in ics1
    assert b"API v2 sunset" in ics1
    assert b"20251201" in ics1 or b"2025-12-01" in ics1


def test_events_to_ics_valid():
    events = _sample_events()
    ics = events_to_ics(events)
    from icalendar import Calendar
    cal = Calendar.from_ical(ics)
    assert cal is not None


def test_report_to_ics():
    report = PlatformReport(
        platform="test",
        generated_at=datetime.utcnow(),
        events=_sample_events(),
        token_metadata={},
    )
    ics = report_to_ics(report)
    assert b"VCALENDAR" in ics
