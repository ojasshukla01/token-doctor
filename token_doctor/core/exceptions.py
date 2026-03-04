"""
Central exception hierarchy for token-doctor.

- TokenDoctorError: base for all token-doctor errors.
- ConfigError / ValidationError: configuration and input validation.
- SecretsError: keychain/secret storage failures.
- NetworkError / APIError / RateLimitError: HTTP and API failures.
- PluginError: plugin loading or execution.
"""

from __future__ import annotations

from typing import Any


class TokenDoctorError(Exception):
    """Base exception for all token-doctor errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigError(TokenDoctorError):
    """Invalid or missing configuration."""


class ValidationError(TokenDoctorError):
    """Input or data validation failed (e.g. invalid platform name, malformed config)."""


class SecretsError(TokenDoctorError):
    """Keychain or encrypted fallback storage failure."""


class NetworkError(TokenDoctorError):
    """Network unreachable, timeout, or connection failure."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        *,
        timeout: bool = False,
        connection_failed: bool = False,
    ) -> None:
        super().__init__(message, details)
        self.timeout = timeout
        self.connection_failed = connection_failed


class APIError(TokenDoctorError):
    """API returned an error response (4xx/5xx)."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        *,
        status_code: int | None = None,
        response_body: str | None = None,
    ) -> None:
        super().__init__(message, details)
        self.status_code = status_code
        self.response_body = response_body


class RateLimitError(APIError):
    """API rate limit exceeded (429 or Retry-After)."""


class AuthenticationError(APIError):
    """Token invalid, expired, or insufficient scope (401/403)."""


class PluginError(TokenDoctorError):
    """Plugin load or execution error."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        *,
        platform: str | None = None,
    ) -> None:
        super().__init__(message, details)
        self.platform = platform
