"""Tests for exception hierarchy and API error handling."""


from token_doctor.core.exceptions import (
    APIError,
    AuthenticationError,
    ConfigError,
    NetworkError,
    PluginError,
    RateLimitError,
    TokenDoctorError,
    ValidationError,
)


def test_base_exception():
    e = TokenDoctorError("msg", {"key": "value"})
    assert str(e) == "msg"
    assert e.message == "msg"
    assert e.details == {"key": "value"}


def test_config_error():
    e = ConfigError("Bad config")
    assert isinstance(e, TokenDoctorError)
    assert e.message == "Bad config"


def test_validation_error():
    e = ValidationError("Invalid input", {"value": "x"})
    assert isinstance(e, TokenDoctorError)
    assert e.details["value"] == "x"


def test_network_error():
    e = NetworkError("Timeout", timeout=True)
    assert e.timeout is True
    assert e.connection_failed is False
    e2 = NetworkError("Connect failed", connection_failed=True)
    assert e2.connection_failed is True


def test_api_error():
    e = APIError("Server error", status_code=500, response_body="Internal")
    assert e.status_code == 500
    assert e.response_body == "Internal"


def test_rate_limit_error():
    e = RateLimitError("Rate limited", status_code=429)
    assert isinstance(e, APIError)
    assert e.status_code == 429


def test_authentication_error():
    e = AuthenticationError("Unauthorized", status_code=401)
    assert isinstance(e, APIError)
    assert e.status_code == 401


def test_plugin_error():
    e = PluginError("Load failed", platform="github")
    assert e.platform == "github"
