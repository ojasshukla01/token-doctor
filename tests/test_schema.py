"""Tests for normalized event schema validation."""

from datetime import datetime, timezone

from token_doctor.core.schema import (
    CheckResult,
    CheckStatus,
    ConfidenceLevel,
    EventType,
    NormalizedEvent,
    PlatformReport,
)


def test_normalized_event_conforms():
    ev = NormalizedEvent(
        platform="github",
        event_type=EventType.DEPRECATION,
        title="Test",
        description="Desc",
        url="https://x.com",
        published_at=datetime.now(timezone.utc),
        effective_date=datetime.now(timezone.utc),
        confidence=ConfidenceLevel.HIGH,
        source_type="rss",
        raw_id="id-1",
        metadata={},
    )
    assert ev.platform == "github"
    assert ev.event_type == EventType.DEPRECATION
    assert ev.raw_id == "id-1"


def test_check_result():
    r = CheckResult(
        name="validity",
        status=CheckStatus.OK,
        message="OK",
        endpoint_used="https://api.example.com/user",
    )
    assert r.status == CheckStatus.OK
    assert r.endpoint_used is not None


def test_platform_report():
    report = PlatformReport(
        platform="github",
        generated_at=datetime.now(timezone.utc),
        events=[],
        token_checks=[],
        token_metadata={"fingerprint": "abc"},
    )
    assert report.platform == "github"
    assert report.generated_at is not None
