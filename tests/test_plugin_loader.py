"""Tests for plugin loader: plugins discovered correctly (A-Z coverage)."""


from token_doctor.core.plugin_loader import (
    get_all_plugins,
    get_plugin_metadata,
)

# Minimum set of platforms that must be present (expanded A-Z + marketing)
EXPECTED_PLATFORMS = [
    "acxiom",
    "adobe",
    "amazon",
    "apple_search_ads",
    "atlassian",
    "auth0",
    "bing_ads",
    "bitbucket",
    "box",
    "braze",
    "brevo",
    "cloudflare",
    "cm360",
    "criteo",
    "digitalocean",
    "discord",
    "dropbox",
    "dv360",
    "github",
    "gitlab",
    "google_ads",
    "heroku",
    "hubspot",
    "instagram",
    "iterable",
    "klaviyo",
    "linear",
    "linkedin",
    "mailchimp",
    "meta_marketing",
    "meta_messenger",
    "microsoft",
    "netlify",
    "notion",
    "pinterest",
    "quora",
    "reddit",
    "sa360",
    "salesforce",
    "segment",
    "sendgrid",
    "sharepoint",
    "slack",
    "snapchat",
    "stripe",
    "taboola",
    "the_trade_desk",
    "tiktok",
    "twilio",
    "twitter",
    "vercel",
    "verizon",
    "whatsapp",
    "yahoo",
    "zoom",
]


def test_plugins_discovered():
    plugins = get_all_plugins()
    for name in EXPECTED_PLATFORMS:
        assert name in plugins, f"Missing platform: {name}"


def test_plugin_count():
    plugins = get_all_plugins()
    assert len(plugins) >= len(EXPECTED_PLATFORMS), (
        f"Expected at least {len(EXPECTED_PLATFORMS)} plugins, got {len(plugins)}"
    )


def test_plugin_metadata():
    plugins = get_all_plugins()
    meta = get_plugin_metadata(plugins["github"])
    assert meta["platform"] == "github"
    assert "declared_endpoints" in meta
    assert "sources_monitored" in meta
    assert "https://api.github.com/user" in meta["declared_endpoints"]


def test_every_plugin_has_required_interface():
    plugins = get_all_plugins()
    for name, plug in plugins.items():
        assert hasattr(plug, "metadata"), f"{name}: missing metadata"
        assert hasattr(plug, "token_checks"), f"{name}: missing token_checks"
        assert hasattr(plug, "collect_changes"), f"{name}: missing collect_changes"
        meta = get_plugin_metadata(plug)
        assert meta.get("platform") == name, f"{name}: metadata.platform mismatch"
