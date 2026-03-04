"""Tests for redaction module: tokens and JWT strings must be masked."""


from token_doctor.core.redaction import (
    REDACT_PLACEHOLDER,
    is_likely_jwt,
    redact_dict,
    redact_exception_message,
    redact_string,
)


def test_redact_jwt():
    s = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0wHSHXXMjz3M9Ecmf1nAyO4F0"
    out = redact_string(s)
    assert "eyJ" not in out
    assert REDACT_PLACEHOLDER in out


def test_redact_github_pat():
    s = "token is ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    out = redact_string(s)
    assert "ghp_" not in out or out.count("ghp_") == 0
    assert REDACT_PLACEHOLDER in out


def test_redact_long_opaque_token():
    s = "api_key=abcdef123456789012345678901234567890abcd"
    out = redact_string(s)
    assert REDACT_PLACEHOLDER in out


def test_redact_dict_secret_keys():
    d = {"user": "alice", "token": "secret123longtoken", "nested": {"password": "mypass"}}
    out = redact_dict(d)
    assert out["token"] == REDACT_PLACEHOLDER
    assert out["nested"]["password"] == REDACT_PLACEHOLDER
    assert out["user"] == "alice"


def test_redact_exception_message():
    class SampleError(Exception):
        pass
    e = SampleError("Failed with token ghp_abcdef123456789012345678901234567890")
    out = redact_exception_message(e)
    assert "ghp_" not in out
    assert REDACT_PLACEHOLDER in out


def test_is_likely_jwt():
    # Pattern requires 20+ chars per segment; last segment 10+
    long_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.xxxxxxxxxx"
    assert is_likely_jwt(long_jwt) is True
    assert is_likely_jwt("ghp_xxxx") is False
    assert is_likely_jwt("") is False
