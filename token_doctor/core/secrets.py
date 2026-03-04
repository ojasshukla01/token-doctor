"""Token storage and retrieval using keyring with encrypted file fallback."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import keyring

SERVICE_NAME = "token-doctor"
KEYRING_AVAILABLE = True
_fallback_path: Path | None = None


def _fallback_file_path(config_dir: Path) -> Path:
    return config_dir / "tokens.encrypted.json"


def _warn_fallback() -> None:
    import warnings

    warnings.warn(
        "Keychain unavailable. Using encrypted file fallback. "
        "Store tokens only in OS keychain when possible.",
        UserWarning,
        stacklevel=2,
    )


def _simple_encrypt(data: str, password: str) -> bytes:
    """Minimal obfuscation for fallback; not cryptographically strong without proper key derivation."""
    import base64

    key = hashlib.sha256(password.encode()).digest()
    raw = data.encode("utf-8")
    out = bytearray(len(raw))
    for i, b in enumerate(raw):
        out[i] = b ^ key[i % len(key)]
    return base64.b64encode(bytes(out))


def _simple_decrypt(data: bytes, password: str) -> str:
    import base64

    key = hashlib.sha256(password.encode()).digest()
    raw = base64.b64decode(data)
    out = bytearray(len(raw))
    for i, b in enumerate(raw):
        out[i] = b ^ key[i % len(key)]
    return out.decode("utf-8")


def get_fallback_password() -> str:
    """Derive fallback encryption password from environment or user home."""
    env_key = os.environ.get("TOKEN_DOCTOR_FALLBACK_KEY")
    if env_key:
        return env_key
    # Use a path-based salt so it's machine-specific
    home = Path.home()
    return hashlib.sha256(str(home).encode()).hexdigest()[:32]


def set_token(platform: str, token: str, config_dir: Path) -> None:
    """Store token in keychain or encrypted fallback."""
    global KEYRING_AVAILABLE
    try:
        keyring.set_password(SERVICE_NAME, platform, token)
        return
    except Exception:
        KEYRING_AVAILABLE = False

    _warn_fallback()
    path = _fallback_file_path(config_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {}
    if path.exists():
        try:
            raw = path.read_bytes()
            payload = json.loads(_simple_decrypt(raw, get_fallback_password()))
        except Exception:
            payload = {}
    payload[platform] = token
    path.write_bytes(_simple_encrypt(json.dumps(payload), get_fallback_password()))


def get_token(platform: str, config_dir: Path) -> str | None:
    """Retrieve token from keychain or fallback."""
    try:
        value = keyring.get_password(SERVICE_NAME, platform)
        if value:
            return value
    except Exception:
        pass

    path = _fallback_file_path(config_dir)
    if not path.exists():
        return None
    try:
        raw = path.read_bytes()
        payload = json.loads(_simple_decrypt(raw, get_fallback_password()))
        val = payload.get(platform)
        return val if isinstance(val, str) else None
    except Exception:
        return None


def delete_token(platform: str, config_dir: Path) -> None:
    """Remove token from keychain and fallback."""
    try:
        keyring.delete_password(SERVICE_NAME, platform)
    except keyring.errors.PasswordDeleteError:
        pass
    except Exception:
        pass

    path = _fallback_file_path(config_dir)
    if path.exists():
        try:
            raw = path.read_bytes()
            payload = json.loads(_simple_decrypt(raw, get_fallback_password()))
            payload.pop(platform, None)
            if payload:
                path.write_bytes(
                    _simple_encrypt(json.dumps(payload), get_fallback_password())
                )
            else:
                path.unlink()
        except Exception:
            pass


def token_fingerprint(token: str) -> str:
    """Return stable hash for display (never the token itself)."""
    return hashlib.sha256(token.encode()).hexdigest()[:16]


def token_last_four(token: str) -> str:
    """Return last 4 characters for user identification."""
    if len(token) < 4:
        return "****"
    return "*" * (len(token) - 4) + token[-4:]
