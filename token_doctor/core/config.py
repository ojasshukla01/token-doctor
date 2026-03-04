"""Configuration loading, profile management, and validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from token_doctor.core.exceptions import ConfigError


class ProfileConfig(BaseModel):
    """Per-platform profile settings."""

    platform: str
    enabled: bool = True
    options: dict[str, Any] = Field(default_factory=dict)


class TokenDoctorConfig(BaseModel):
    """Root configuration model."""

    config_dir: Path = Field(default_factory=lambda: Path.home() / ".config" / "token-doctor")
    db_path: Path | None = None  # default: config_dir / "db" / "cache.sqlite"
    profiles: list[ProfileConfig] = Field(default_factory=list)
    offline: bool = False
    explain: bool = False
    use_bs4: bool = False  # opt-in BeautifulSoup scraping

    @property
    def effective_db_path(self) -> Path:
        if self.db_path is not None:
            return self.db_path
        return self.config_dir / "db" / "cache.sqlite"

    def get_profile(self, platform: str) -> ProfileConfig | None:
        for p in self.profiles:
            if p.platform == platform:
                return p
        return None

    def add_profile(self, platform: str, options: dict[str, Any] | None = None) -> None:
        existing = self.get_profile(platform)
        if existing:
            existing.enabled = True
            if options:
                existing.options.update(options)
            return
        self.profiles.append(
            ProfileConfig(platform=platform, enabled=True, options=options or {})
        )

    def remove_profile(self, platform: str) -> None:
        self.profiles = [p for p in self.profiles if p.platform != platform]


def load_config(config_path: Path | None = None) -> TokenDoctorConfig:
    """Load config from path or default location. Raises ConfigError on invalid JSON or schema."""
    default_dir = Path.home() / ".config" / "token-doctor"
    config_file = config_path or default_dir / "config.json"
    path = config_file if isinstance(config_file, Path) else Path(config_file)
    if not path.exists():
        return TokenDoctorConfig(config_dir=path.parent)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ConfigError(f"Invalid config JSON: {e}", {"path": str(path)}) from e
    if not isinstance(data, dict):
        raise ConfigError("Config must be a JSON object.", {"path": str(path)})
    # Normalize paths
    if "config_dir" in data and data["config_dir"]:
        data["config_dir"] = Path(data["config_dir"])
    if data.get("db_path"):
        data["db_path"] = Path(data["db_path"])
    try:
        return TokenDoctorConfig(**{k: v for k, v in data.items() if k in TokenDoctorConfig.model_fields})
    except Exception as e:
        raise ConfigError(f"Invalid config: {e}", {"path": str(path)}) from e


def save_config(config: TokenDoctorConfig, config_path: Path | None = None) -> None:
    """Persist config to JSON."""
    path = config_path or config.config_dir / "config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    out = config.model_dump()
    out["config_dir"] = str(config.config_dir)
    if config.db_path:
        out["db_path"] = str(config.db_path)
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")


def ensure_config_dir(config: TokenDoctorConfig) -> None:
    """Create config directory and db subdirectory."""
    config.config_dir.mkdir(parents=True, exist_ok=True)
    (config.config_dir / "db").mkdir(parents=True, exist_ok=True)
