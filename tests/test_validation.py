"""Tests for validation module: platform names, token length, config."""

import pytest

from token_doctor.core.exceptions import ValidationError
from token_doctor.core.validation import (
    MIN_TOKEN_LENGTH,
    PLATFORM_NAME_PATTERN,
    validate_platform_name,
    validate_token_not_empty,
)


def test_platform_name_valid():
    assert validate_platform_name("github") == "github"
    assert validate_platform_name("  slack  ") == "slack"
    assert validate_platform_name("google_ads") == "google_ads"
    assert validate_platform_name("meta_marketing") == "meta_marketing"


def test_platform_name_invalid():
    with pytest.raises(ValidationError):
        validate_platform_name("")
    with pytest.raises(ValidationError):
        validate_platform_name("Git-Hub")  # hyphen not allowed
    with pytest.raises(ValidationError):
        validate_platform_name("123abc")  # must start with letter
    assert PLATFORM_NAME_PATTERN.match("a1") is not None
    assert PLATFORM_NAME_PATTERN.match("1a") is None


def test_token_not_empty():
    long_token = "x" * MIN_TOKEN_LENGTH
    assert validate_token_not_empty(long_token) == long_token
    with pytest.raises(ValidationError):
        validate_token_not_empty("short")
    with pytest.raises(ValidationError):
        validate_token_not_empty(None)
    with pytest.raises(ValidationError):
        validate_token_not_empty("   ")
