"""Tests for config loading and validation."""


import pytest

from token_doctor.core.config import (
    TokenDoctorConfig,
    ensure_config_dir,
    load_config,
    save_config,
)
from token_doctor.core.exceptions import ConfigError


def test_load_config_missing_file(tmp_path):
    """When config file does not exist, return default config."""
    config = load_config(tmp_path / "config.json")
    assert config.config_dir == tmp_path
    assert config.profiles == []


def test_load_config_invalid_json(tmp_path):
    """Invalid JSON raises ConfigError."""
    config_file = tmp_path / "config.json"
    config_file.write_text("{ invalid }")
    with pytest.raises(ConfigError) as exc_info:
        load_config(config_file)
    assert "JSON" in exc_info.value.message or "Invalid" in exc_info.value.message


def test_save_and_load_roundtrip(tmp_path):
    """Save config and load it back."""
    config = TokenDoctorConfig(config_dir=tmp_path)
    config.add_profile("github")
    ensure_config_dir(config)
    save_config(config)
    loaded = load_config(tmp_path / "config.json")
    assert len(loaded.profiles) == 1
    assert loaded.profiles[0].platform == "github"
