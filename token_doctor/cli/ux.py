"""CLI UX helpers: fuzzy platform suggestion, platform hints, optional Rich."""

from __future__ import annotations

import difflib

# Generic next-step hint for platforms that do not require extra config
_NEXT_STEP = "Store your token with: token-doctor token set {platform}."

# Platform-specific hints shown after profile add (config options or next step).
# Every available platform/plugin MUST have an entry here. When adding a new platform:
# 1. Add an entry to PLATFORM_HINTS (custom hint or _NEXT_STEP.format(platform="...")).
# 2. Update EXPECTED_PLATFORMS in tests/test_plugin_loader.py and docs (README, docs/sources.md).
# See CONTRIBUTING.md for the full checklist. test_platform_hints_cover_all_plugins will fail until this is done.
PLATFORM_HINTS: dict[str, str] = {
    "acxiom": _NEXT_STEP.format(platform="acxiom"),
    "adobe": _NEXT_STEP.format(platform="adobe"),
    "amazon": _NEXT_STEP.format(platform="amazon"),
    "apple_search_ads": _NEXT_STEP.format(platform="apple_search_ads"),
    "atlassian": "Set 'base_url' in profile options for Jira/Confluence (e.g. https://your-site.atlassian.net).",
    "auth0": "Set 'tenant' in profile options for Auth0 (e.g. mycompany).",
    "bing_ads": _NEXT_STEP.format(platform="bing_ads"),
    "bitbucket": _NEXT_STEP.format(platform="bitbucket"),
    "box": _NEXT_STEP.format(platform="box"),
    "braze": "Set 'rest_url' in profile options for Braze (e.g. https://rest.iad-01.braze.com).",
    "brevo": _NEXT_STEP.format(platform="brevo"),
    "cloudflare": _NEXT_STEP.format(platform="cloudflare"),
    "cm360": _NEXT_STEP.format(platform="cm360"),
    "criteo": _NEXT_STEP.format(platform="criteo"),
    "digitalocean": _NEXT_STEP.format(platform="digitalocean"),
    "discord": _NEXT_STEP.format(platform="discord"),
    "dropbox": _NEXT_STEP.format(platform="dropbox"),
    "dv360": _NEXT_STEP.format(platform="dv360"),
    "github": _NEXT_STEP.format(platform="github"),
    "gitlab": _NEXT_STEP.format(platform="gitlab"),
    "google_ads": _NEXT_STEP.format(platform="google_ads"),
    "heroku": _NEXT_STEP.format(platform="heroku"),
    "hubspot": _NEXT_STEP.format(platform="hubspot"),
    "instagram": _NEXT_STEP.format(platform="instagram"),
    "iterable": _NEXT_STEP.format(platform="iterable"),
    "klaviyo": _NEXT_STEP.format(platform="klaviyo"),
    "linear": _NEXT_STEP.format(platform="linear"),
    "linkedin": _NEXT_STEP.format(platform="linkedin"),
    "mailchimp": "Set 'dc' (datacenter, e.g. us1) in profile options for Mailchimp.",
    "meta_marketing": _NEXT_STEP.format(platform="meta_marketing"),
    "meta_messenger": _NEXT_STEP.format(platform="meta_messenger"),
    "microsoft": _NEXT_STEP.format(platform="microsoft"),
    "netlify": _NEXT_STEP.format(platform="netlify"),
    "notion": _NEXT_STEP.format(platform="notion"),
    "pinterest": _NEXT_STEP.format(platform="pinterest"),
    "quora": _NEXT_STEP.format(platform="quora"),
    "reddit": _NEXT_STEP.format(platform="reddit"),
    "sa360": _NEXT_STEP.format(platform="sa360"),
    "salesforce": "Set 'instance_url' in profile options for Salesforce (e.g. https://mycompany.my.salesforce.com).",
    "segment": _NEXT_STEP.format(platform="segment"),
    "sendgrid": _NEXT_STEP.format(platform="sendgrid"),
    "sharepoint": _NEXT_STEP.format(platform="sharepoint"),
    "slack": _NEXT_STEP.format(platform="slack"),
    "snapchat": _NEXT_STEP.format(platform="snapchat"),
    "stripe": _NEXT_STEP.format(platform="stripe"),
    "taboola": _NEXT_STEP.format(platform="taboola"),
    "the_trade_desk": _NEXT_STEP.format(platform="the_trade_desk"),
    "tiktok": _NEXT_STEP.format(platform="tiktok"),
    "twilio": _NEXT_STEP.format(platform="twilio"),
    "twitter": _NEXT_STEP.format(platform="twitter"),
    "vercel": _NEXT_STEP.format(platform="vercel"),
    "verizon": _NEXT_STEP.format(platform="verizon"),
    "whatsapp": _NEXT_STEP.format(platform="whatsapp"),
    "yahoo": _NEXT_STEP.format(platform="yahoo"),
    "zoom": _NEXT_STEP.format(platform="zoom"),
}


def suggest_platform(unknown: str, available: list[str], cutoff: float = 0.5) -> str | None:
    """Return closest matching platform name or None."""
    if not available:
        return None
    matches = difflib.get_close_matches(unknown, available, n=1, cutoff=cutoff)
    return matches[0] if matches else None


def get_platform_hint(platform: str) -> str | None:
    """Return a one-line hint for the platform if any."""
    return PLATFORM_HINTS.get(platform)


def try_rich_table(headers: list[str], rows: list[list[str]]) -> bool:
    """If Rich is available, print table and return True; else return False."""
    try:
        from rich.console import Console
        from rich.table import Table
        table = Table()
        for h in headers:
            table.add_column(h)
        for row in rows:
            table.add_row(*row)
        Console().print(table)
        return True
    except ImportError:
        return False


def echo_next_step_init() -> None:
    """Print next-step hint after init."""
    import typer
    typer.echo("Next: token-doctor profile add <platform>")
    typer.echo("Then: token-doctor token set <platform>")


def echo_next_step_token_check_failed(platform: str) -> None:
    """Print hint when token check failed (no token or invalid)."""
    import typer
    typer.echo(f"Consider: token-doctor token set {platform}", err=True)
