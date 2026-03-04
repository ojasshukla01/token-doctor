"""Detect and redact tokens/JWT-like strings from logs, output, and reports."""

from __future__ import annotations

import re
from typing import Any

# JWT: base64url.base64url.base64url
JWT_PATTERN = re.compile(
    r"\beyJ[A-Za-z0-9_-]{20,}\.eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\b"
)
# Generic bearer / API key patterns (avoid matching short strings)
BEARER_PATTERN = re.compile(
    r"(?i)(bearer|token|api[_-]?key|authorization)\s*[:=]\s*[\"']?([A-Za-z0-9_\-\.~]+){20,}[\"']?",
    re.IGNORECASE,
)
# GitHub-style token
GH_PATTERN = re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{36,}\b")
# Generic long alphanumeric token (40+ chars)
LONG_TOKEN_PATTERN = re.compile(r"\b[A-Za-z0-9_\-]{40,}\b")

REDACT_PLACEHOLDER = "***REDACTED***"


def redact_string(value: str) -> str:
    """Redact tokens and JWT-like strings in a string."""
    if not value or not isinstance(value, str):
        return value
    out = value
    out = JWT_PATTERN.sub(REDACT_PLACEHOLDER, out)
    out = BEARER_PATTERN.sub(r"\1: " + REDACT_PLACEHOLDER, out)
    out = GH_PATTERN.sub(REDACT_PLACEHOLDER, out)
    # Apply long-token pattern last and only to remaining long strings
    def replace_long(m: re.Match[str]) -> str:
        s = m.group(0)
        if s == REDACT_PLACEHOLDER or s.isdigit():
            return s
        return REDACT_PLACEHOLDER

    out = LONG_TOKEN_PATTERN.sub(replace_long, out)
    return out


def redact_dict(obj: dict[str, Any], depth: int = 0) -> dict[str, Any]:
    """Recursively redact string values in a dict. Keys like 'token' are always redacted."""
    if depth > 20:
        return obj
    out: dict[str, Any] = {}
    secret_keys = {"token", "password", "secret", "authorization", "api_key", "apikey"}
    for k, v in obj.items():
        key_lower = k.lower() if isinstance(k, str) else ""
        if key_lower in secret_keys and isinstance(v, str):
            out[k] = REDACT_PLACEHOLDER
        elif isinstance(v, str):
            out[k] = redact_string(v)
        elif isinstance(v, dict):
            out[k] = redact_dict(v, depth + 1)
        elif isinstance(v, list):
            out[k] = [redact_dict(x, depth + 1) if isinstance(x, dict) else (redact_string(x) if isinstance(x, str) else x) for x in v]
        else:
            out[k] = v
    return out


def redact_exception_message(exc: BaseException) -> str:
    """Return redacted exception message."""
    return redact_string(str(exc))


def is_likely_jwt(value: str) -> bool:
    """Heuristic: value looks like a JWT."""
    return bool(JWT_PATTERN.match(value.strip()) if value else False)
