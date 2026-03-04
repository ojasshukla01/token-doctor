"""Twilio plugin: token check via /2010-04-01/Accounts (Account SID + Auth Token), changelog from blog."""

from __future__ import annotations

import base64
from typing import Any

from token_doctor.core.http_client import get
from token_doctor.core.schema import CheckResult, CheckStatus, NormalizedEvent
from token_doctor.platforms.base import safe_fetch_feed

# Twilio uses Basic auth: Account SID as username, Auth Token as password.
# Token stored in token-doctor is expected as "AccountSid:AuthToken" or we use token as Auth Token and need sid in config.
DECLARED_ENDPOINTS = ["https://api.twilio.com/2010-04-01/Accounts.json"]
CHANGELOG_FEEDS = [
    "https://www.twilio.com/blog/feed",
]
DOCS_LINKS = ["https://www.twilio.com/docs/usage/api", "https://www.twilio.com/blog"]

metadata = {
    "platform": "twilio",
    "auth_types": ["account_sid_and_auth_token", "api_key_secret"],
    "documentation_links": DOCS_LINKS,
    "declared_endpoints": DECLARED_ENDPOINTS,
    "sources_monitored": CHANGELOG_FEEDS,
    "data_collected": ["account list (friendly_name) for validation", "blog feed entries"],
}


def _basic_auth(sid: str, secret: str) -> str:
    """Build Basic auth header value (base64)."""
    raw = f"{sid}:{secret}"
    return "Basic " + base64.b64encode(raw.encode()).decode()


def token_checks(token: str, config: Any) -> list[CheckResult]:
    """
    Validate Twilio credentials. Token can be 'AccountSid:AuthToken' or Auth Token only.
    If only Auth Token, config profile option 'account_sid' must be set.
    """
    results: list[CheckResult] = []
    endpoint = "https://api.twilio.com/2010-04-01/Accounts.json"
    try:
        if ":" in token and not token.startswith("SK"):
            sid, secret = token.split(":", 1)
            auth_header = _basic_auth(sid.strip(), secret.strip())
        else:
            sid = None
            if config and getattr(config, "get_profile", None):
                profile = config.get_profile("twilio")
                if profile and profile.options.get("account_sid"):
                    sid = profile.options["account_sid"]
            if not sid:
                results.append(
                    CheckResult(
                        name="validity",
                        status=CheckStatus.SKIPPED,
                        message="Set token as 'AccountSid:AuthToken' or set profile option account_sid and token as Auth Token.",
                        endpoint_used=endpoint,
                    )
                )
                return results
            auth_header = _basic_auth(sid, token)
        resp = get(
            endpoint,
            headers={"Authorization": auth_header},
            raise_for_status=False,
        )
        if resp.status_code == 200:
            data = resp.json() if resp.content else {}
            accounts = data.get("accounts", [])
            if accounts:
                name = accounts[0].get("friendly_name", "?")
                results.append(
                    CheckResult(
                        name="validity",
                        status=CheckStatus.OK,
                        message=f"Credentials valid (account: {name})",
                        details={"friendly_name": name},
                        endpoint_used=endpoint,
                    )
                )
            else:
                results.append(
                    CheckResult(
                        name="validity",
                        status=CheckStatus.OK,
                        message="Credentials valid",
                        endpoint_used=endpoint,
                    )
                )
        elif resp.status_code in (401, 403):
            results.append(
                CheckResult(
                    name="validity",
                    status=CheckStatus.ERROR,
                    message="Invalid Account SID or Auth Token",
                    endpoint_used=endpoint,
                )
            )
        else:
            results.append(
                CheckResult(
                    name="validity",
                    status=CheckStatus.WARNING,
                    message=f"Unexpected status {resp.status_code}",
                    details={"status_code": resp.status_code},
                    endpoint_used=endpoint,
                )
            )
    except Exception as e:
        results.append(
            CheckResult(
                name="validity",
                status=CheckStatus.ERROR,
                message=str(e)[:200],
                endpoint_used=endpoint,
            )
        )
    return results


def collect_changes(since: Any) -> list[NormalizedEvent]:
    events: list[NormalizedEvent] = []
    for url in CHANGELOG_FEEDS:
        events.extend(safe_fetch_feed(url, "twilio", since=since))
    return events


def collect_status() -> None:
    return None


plugin = type("TwilioPlugin", (), {
    "metadata": metadata,
    "token_checks": lambda self, token, config: token_checks(token, config),
    "collect_changes": lambda self, since: collect_changes(since),
    "collect_status": lambda self: collect_status(),
})()
