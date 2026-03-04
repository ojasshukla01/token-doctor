"""JWT parsing for local expiry inference. No network calls."""

from __future__ import annotations

import base64
import json
from datetime import datetime
from typing import Any, cast


def _b64_decode(s: str) -> bytes:
    pad = 4 - len(s) % 4
    if pad != 4:
        s += "=" * pad
    return base64.urlsafe_b64decode(s)


def decode_jwt_payload(token: str) -> dict[str, Any] | None:
    """Decode JWT payload without verification (local inspection only). Returns None on failure."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        payload_b64 = parts[1]
        raw = _b64_decode(payload_b64)
        return cast("dict[str, Any]", json.loads(raw))
    except Exception:
        return None


def get_jwt_expiry(token: str) -> datetime | None:
    """Infer expiry from JWT 'exp' claim if present. Returns None if not JWT or no exp."""
    payload = decode_jwt_payload(token)
    if not payload:
        return None
    exp = payload.get("exp")
    if exp is None:
        return None
    if isinstance(exp, int | float):
        return datetime.utcfromtimestamp(exp)
    return None
