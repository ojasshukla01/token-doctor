"""Tests for newly added features: platform hints, status, dashboard, expiring, cache helpers, report HTML, lazy plugins, CLI."""

from __future__ import annotations

import os
from unittest.mock import patch

from typer.testing import CliRunner

from tests.test_plugin_loader import EXPECTED_PLATFORMS
from token_doctor.cli.main import app
from token_doctor.cli.ux import PLATFORM_HINTS, get_platform_hint, suggest_platform
from token_doctor.core.cache import (
    get_event_counts,
    get_next_deadlines,
    init_db,
    upsert_events,
)
from token_doctor.core.config import TokenDoctorConfig, ensure_config_dir, save_config
from token_doctor.core.plugin_loader import get_all_plugins, list_platform_names
from token_doctor.core.reporting import report_to_html
from token_doctor.core.schema import (
    ConfidenceLevel,
    EventType,
    NormalizedEvent,
    PlatformReport,
)


def test_platform_hints_cover_all_plugins():
    """Every discovered platform has an entry in PLATFORM_HINTS.

    When adding a new platform, add PLATFORM_HINTS in token_doctor/cli/ux.py and
    update EXPECTED_PLATFORMS, README, and docs/sources.md. See CONTRIBUTING.md.
    """
    plugins = get_all_plugins()
    for name in plugins:
        assert name in PLATFORM_HINTS, f"PLATFORM_HINTS missing entry for platform: {name}"


def test_platform_hints_expected_platforms_have_hints():
    """Every expected platform (test_plugin_loader) has a hint.

    Keeps PLATFORM_HINTS in sync with EXPECTED_PLATFORMS. See CONTRIBUTING.md for
    the full checklist when adding a new platform.
    """
    for name in EXPECTED_PLATFORMS:
        assert name in PLATFORM_HINTS, f"PLATFORM_HINTS missing entry for: {name}"


def test_suggest_platform_suggests_for_typo():
    """Fuzzy match suggests 'github' for 'githb'."""
    available = list_platform_names()
    assert suggest_platform("githb", available) == "github"
    assert suggest_platform("slak", available) == "slack"


def test_suggest_platform_none_for_unknown():
    """No suggestion for completely unknown name."""
    available = list_platform_names()
    assert suggest_platform("xyznonexistent", available) is None


def test_suggest_platform_exact_match():
    """Exact platform name returns itself (or closest)."""
    available = list_platform_names()
    assert suggest_platform("github", available) == "github"


def test_get_platform_hint_for_config_platforms():
    """Platforms that need config return specific hint."""
    assert "tenant" in (get_platform_hint("auth0") or "")
    assert "base_url" in (get_platform_hint("atlassian") or "")
    assert "instance_url" in (get_platform_hint("salesforce") or "")
    assert "rest_url" in (get_platform_hint("braze") or "")
    assert "dc" in (get_platform_hint("mailchimp") or "").lower()


def test_get_platform_hint_for_generic_platforms():
    """Generic platforms return next-step hint containing token set."""
    hint = get_platform_hint("github")
    assert hint is not None
    assert "token set" in hint
    assert "github" in hint


def test_cache_get_event_counts_empty(tmp_path):
    """get_event_counts on empty DB returns empty or zero counts."""
    db = tmp_path / "cache.sqlite"
    init_db(db)
    counts = get_event_counts(db)
    assert counts == {}
    counts_one = get_event_counts(db, platform="github")
    assert counts_one.get("github", 0) == 0


def test_cache_get_event_counts_after_upsert(tmp_path):
    """get_event_counts returns counts per platform after upsert_events."""
    db = tmp_path / "cache.sqlite"
    init_db(db)
    from datetime import datetime, timezone
    events = [
        NormalizedEvent(
            platform="github",
            event_type=EventType.ANNOUNCEMENT,
            title="E",
            description="D",
            url=None,
            published_at=datetime.now(timezone.utc),
            effective_date=None,
            confidence=ConfidenceLevel.HIGH,
            source_type="rss",
            raw_id="1",
            metadata={},
        ),
        NormalizedEvent(
            platform="github",
            event_type=EventType.ANNOUNCEMENT,
            title="E2",
            description="D2",
            url=None,
            published_at=datetime.now(timezone.utc),
            effective_date=None,
            confidence=ConfidenceLevel.HIGH,
            source_type="rss",
            raw_id="2",
            metadata={},
        ),
        NormalizedEvent(
            platform="slack",
            event_type=EventType.ANNOUNCEMENT,
            title="S",
            description="D",
            url=None,
            published_at=datetime.now(timezone.utc),
            effective_date=None,
            confidence=ConfidenceLevel.HIGH,
            source_type="rss",
            raw_id="1",
            metadata={},
        ),
    ]
    upsert_events(db, events)
    counts = get_event_counts(db)
    assert counts.get("github") == 2
    assert counts.get("slack") == 1
    counts_github = get_event_counts(db, platform="github")
    assert counts_github == {"github": 2}


def test_cache_get_next_deadlines_empty(tmp_path):
    """get_next_deadlines on empty DB returns empty list."""
    db = tmp_path / "cache.sqlite"
    init_db(db)
    deadlines = get_next_deadlines(db, limit=5)
    assert deadlines == []


def test_report_to_html_contains_platform():
    """report_to_html produces HTML containing platform name."""
    from datetime import datetime, timezone
    report = PlatformReport(
        platform="test_platform",
        generated_at=datetime.now(timezone.utc),
        events=[],
        token_checks=[],
        token_metadata={},
    )
    html = report_to_html(report)
    assert "test_platform" in html
    assert "<!DOCTYPE html>" in html
    assert "</body>" in html


def test_lazy_plugins_only_loads_requested():
    """get_all_plugins(only_platforms=[...]) returns only those platforms."""
    plugins = get_all_plugins(only_platforms=["github", "slack"])
    assert set(plugins.keys()) <= {"github", "slack"}
    assert "github" in plugins
    assert "slack" in plugins


def test_token_set_env_reads_from_env(tmp_path):
    """token set --env VAR uses environment variable (integration via CLI)."""
    config = TokenDoctorConfig(config_dir=tmp_path)
    ensure_config_dir(config)
    save_config(config)
    init_db(config.effective_db_path)
    config.add_profile("github")
    save_config(config)
    with (
        patch.dict(os.environ, {"TEST_TOKEN_ENV": "ghp_abcdef123456789012345678901234"}, clear=False),
        patch("token_doctor.cli.main.load_config", return_value=config),
    ):
        runner = CliRunner()
        result = runner.invoke(app, ["token", "set", "github", "--env", "TEST_TOKEN_ENV"])
    assert result.exit_code == 0
    assert "stored" in result.output.lower()


def test_init_prints_next_step(tmp_path):
    """init prints next-step hint."""
    runner = CliRunner()
    result = runner.invoke(app, ["init", "--config-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "Initialized config" in result.output
    assert "Next:" in result.output or "profile add" in result.output


def test_status_command_exits_zero(tmp_path):
    """status command runs and exits 0 (no profiles is ok)."""
    config = TokenDoctorConfig(config_dir=tmp_path)
    ensure_config_dir(config)
    save_config(config)
    init_db(config.effective_db_path)
    with patch("token_doctor.cli.main.load_config", return_value=config):
        runner = CliRunner()
        result = runner.invoke(app, ["status"])
    assert result.exit_code == 0


def test_expiring_command_exits_zero(tmp_path):
    """expiring command runs and exits 0."""
    config = TokenDoctorConfig(config_dir=tmp_path)
    ensure_config_dir(config)
    save_config(config)
    with patch("token_doctor.cli.main.load_config", return_value=config):
        runner = CliRunner()
        result = runner.invoke(app, ["expiring", "--days", "7"])
    assert result.exit_code == 0
    assert "No tokens" in result.output or "expir" in result.output.lower()


def test_dashboard_command_exits_zero(tmp_path):
    """dashboard command runs and exits 0."""
    config = TokenDoctorConfig(config_dir=tmp_path)
    ensure_config_dir(config)
    save_config(config)
    init_db(config.effective_db_path)
    with patch("token_doctor.cli.main.load_config", return_value=config):
        runner = CliRunner()
        result = runner.invoke(app, ["dashboard"])
    assert result.exit_code == 0


def test_profile_add_prints_hint_for_platform_with_hint(tmp_path):
    """profile add auth0 prints platform-specific hint."""
    config = TokenDoctorConfig(config_dir=tmp_path)
    ensure_config_dir(config)
    save_config(config)
    with patch("token_doctor.cli.main.load_config", return_value=config):
        runner = CliRunner()
        result = runner.invoke(app, ["profile", "add", "auth0"])
    assert result.exit_code == 0
    assert "Tip:" in result.output
    assert "tenant" in result.output


def test_report_format_html_writes_file(tmp_path):
    """report with --format html writes .html file."""
    config = TokenDoctorConfig(config_dir=tmp_path)
    ensure_config_dir(config)
    save_config(config)
    config.add_profile("github")
    save_config(config)
    init_db(config.effective_db_path)
    out_dir = tmp_path / "reports"
    with patch("token_doctor.cli.main.load_config", return_value=config):
        runner = CliRunner()
        result = runner.invoke(app, ["report", "github", "--output-dir", str(out_dir), "--format", "html"])
    assert result.exit_code == 0
    html_file = out_dir / "github.html"
    assert html_file.exists()
    assert "github" in html_file.read_text()


def test_doctor_run_ci_exits_zero_when_no_critical(tmp_path):
    """doctor run --ci exits 0 when no critical event within 30 days."""
    config = TokenDoctorConfig(config_dir=tmp_path)
    ensure_config_dir(config)
    config.add_profile("github")
    save_config(config)
    init_db(config.effective_db_path)
    with patch("token_doctor.cli.main.load_config", return_value=config):
        runner = CliRunner()
        result = runner.invoke(app, ["doctor", "run", "github", "--ci"])
    # May exit 0 or 1 (token check fail); should not exit 2 (critical event) when cache is empty
    assert result.exit_code in (0, 1)
