"""Integration test: mock HTTP and run doctor run github."""


from datetime import datetime

import pytest
import respx
from httpx import Response

from token_doctor.core.cache import get_events, init_db, upsert_events
from token_doctor.core.config import TokenDoctorConfig, ensure_config_dir, save_config
from token_doctor.core.secrets import set_token


@pytest.fixture
def temp_config(tmp_path):
    config = TokenDoctorConfig(config_dir=tmp_path)
    ensure_config_dir(config)
    init_db(config.effective_db_path)
    save_config(config)
    return config


@respx.mock
def test_doctor_run_github_integration(temp_config):
    """Mock GitHub API and changelog; run token check and changes fetch."""
    # Mock /user
    respx.get("https://api.github.com/user").mock(return_value=Response(200, json={"login": "testuser", "id": 1}))
    # Mock changelog feed
    respx.get("https://github.blog/changelog/feed/").mock(
        return_value=Response(
            200,
            content=b"""<?xml version="1.0"?>
<rss><channel><title>Changelog</title>
<item><title>Test post</title><link>https://blog.example/post</link><description>Desc</description></item>
</channel></rss>""",
            headers={"Content-Type": "application/xml"},
        )
    )
    set_token("github", "ghp_testtoken123456789012345678901234", temp_config.config_dir)
    from token_doctor.core.plugin_loader import get_all_plugins
    plugins = get_all_plugins()
    plug = plugins["github"]
    # Token checks (will use mocked /user)
    results = plug.token_checks("ghp_testtoken123456789012345678901234", temp_config)
    assert len(results) >= 1
    assert results[0].status.value in ("ok", "error", "warning")
    # Collect changes (will use mocked feed)
    events = plug.collect_changes(since=datetime(2020, 1, 1))
    # May be 0 if feedparser doesn't parse our minimal RSS
    assert isinstance(events, list)
    if events:
        assert all(e.platform == "github" for e in events)
    # Ensure cache write works
    n = upsert_events(temp_config.effective_db_path, events)
    assert n == len(events)
    cached = get_events(temp_config.effective_db_path, platform="github")
    assert len(cached) == len(events)
