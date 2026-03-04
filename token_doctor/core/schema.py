"""Normalized data models for token checks, events, and platform reports."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class CheckStatus(str, Enum):
    """Result status of a token check."""

    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    SKIPPED = "skipped"


class EventType(str, Enum):
    """Type of platform change event."""

    SUNSET = "sunset"
    DEPRECATION = "deprecation"
    MAINTENANCE = "maintenance"
    VERSION_UPGRADE = "version_upgrade"
    BREAKING_CHANGE = "breaking_change"
    ANNOUNCEMENT = "announcement"
    OTHER = "other"


class ConfidenceLevel(str, Enum):
    """Confidence in event source."""

    HIGH = "high"  # official API docs feed
    MEDIUM = "medium"  # official vendor blog
    LOW = "low"  # scraped HTML


@dataclass
class CheckResult:
    """Result of a single token validation check."""

    name: str
    status: CheckStatus
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    endpoint_used: str | None = None


@dataclass
class NormalizedEvent:
    """Normalized platform change event."""

    platform: str
    event_type: EventType
    title: str
    description: str
    url: str | None
    published_at: datetime | None
    effective_date: datetime | None  # sunset/migration deadline
    confidence: ConfidenceLevel
    source_type: str  # e.g. "rss", "blog", "scraped"
    raw_id: str  # stable id from source
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PlatformReport:
    """Aggregated report for a platform."""

    platform: str
    generated_at: datetime
    events: list[NormalizedEvent]
    token_checks: list[CheckResult] = field(default_factory=list)
    token_metadata: dict[str, Any] = field(default_factory=dict)
