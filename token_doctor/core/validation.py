"""
Validation and verification helpers.

- Platform names, config values, and input sanitization.
- Used by CLI and core to avoid human error and mishaps.
"""

from __future__ import annotations

import re
from pathlib import Path

from token_doctor.core.exceptions import ValidationError

# Allowed platform name: alphanumeric and underscore only.
PLATFORM_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")

# Minimum token length to avoid accidental empty or trivial input.
MIN_TOKEN_LENGTH = 10


def validate_platform_name(name: str) -> str:
    """
    Validate and normalize platform name.
    Raises ValidationError if invalid.
    """
    if not name or not isinstance(name, str):
        raise ValidationError("Platform name is required.", {"value": str(name)})
    normalized = name.strip().lower()
    if not PLATFORM_NAME_PATTERN.match(normalized):
        raise ValidationError(
            "Platform name must be lowercase, start with a letter, and contain only letters, digits, and underscores.",
            {"value": normalized},
        )
    return normalized


def validate_token_not_empty(token: str | None) -> str:
    """
    Ensure token is non-empty and not obviously too short.
    Does NOT validate format or strength.
    """
    if token is None:
        raise ValidationError("Token cannot be None.", {})
    s = token.strip()
    if len(s) < MIN_TOKEN_LENGTH:
        raise ValidationError(
            "Token is too short; it may be incomplete or pasted incorrectly.",
            {"length": len(s), "min": MIN_TOKEN_LENGTH},
        )
    return s


def validate_config_dir(path: Path) -> Path:
    """Ensure config directory path is valid and writable (or parent exists)."""
    p = Path(path).resolve()
    if p.exists() and not p.is_dir():
        raise ValidationError("Config path must be a directory.", {"path": str(p)})
    return p


def validate_output_path(path: Path, must_exist: bool = False) -> Path:
    """Validate output file or directory path."""
    p = Path(path).resolve()
    if must_exist and not p.exists():
        raise ValidationError("Output path does not exist.", {"path": str(p)})
    return p
