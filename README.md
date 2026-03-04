# token-doctor

A **local-first** CLI that helps you debug API tokens, track platform changes, and never miss a sunset or migration deadline.

**What it does:**

- **Debug tokens safely** — Validate tokens, detect type, infer JWT expiry, see scopes. Everything stays on your machine; tokens are stored in your OS keychain and never printed or sent anywhere.
- **Track API changes** — Pull maintenance notices, deprecations, and sunset dates from official feeds (blogs, changelogs, RSS).
- **Calendar alerts** — Export ICS files for sunsets, deadlines, maintenance windows, and token expiry so you can plug them into Outlook, Google Calendar, or any calendar app.
- **Reports** — Per-platform or combined Markdown and JSON reports for sharing (redacted) or scripting.

**Security:** Local-only. No telemetry. Optional offline mode. Automatic redaction when sharing.

---

## Quick start

**Install (choose one):**

```bash
# With Poetry
poetry install

# Without Poetry — install in your environment
pip install -e .
```

If the `token-doctor` script isn’t on your PATH (common with Windows Store Python), use the module instead:

```bash
python -m token_doctor.cli.main
```

**First-time setup:**

```bash
# Create config directory, SQLite DB, and sample config
token-doctor init
# or: python -m token_doctor.cli.main init

# Add a platform (e.g. GitHub)
token-doctor profile add github

# Store your token in the OS keychain (you’ll be prompted)
token-doctor token set github

# Check that the token works
token-doctor token check github
```

**Daily use:**

```bash
# Fetch latest changelog/feed data for the platform
token-doctor changes fetch github

# Generate Markdown + JSON report
token-doctor report github

# Export an ICS calendar (sunsets, deadlines, maintenance, token expiry)
token-doctor calendar export github -o calendar.ics

# Or do everything in one go: check token, fetch changes, report, calendar
token-doctor doctor run github
```

---

## Commands (what each one does)

| Command | What it does |
|--------|----------------|
| **`init`** | Creates the config directory (e.g. `~/.config/token-doctor`), initializes the SQLite cache DB, and writes a sample config so you can start adding platforms. |
| **`profile add <platform>`** | Adds a platform to your config so you can store a token and run checks/changes for it. |
| **`profile list`** | Lists all platforms you’ve added. |
| **`profile remove <platform>`** | Removes a platform from your config (does not delete the token from the keychain; use `token delete` for that). |
| **`token set <platform>`** | Prompts for a token and stores it in the OS keychain (or encrypted file fallback if keychain isn’t available). |
| **`token info <platform>`** | Shows non-secret metadata about the stored token (e.g. last four chars, fingerprint); never prints the token. |
| **`token check <platform>`** | Runs the platform’s validation (e.g. calls `/user` or equivalent) and reports if the token is valid, expired, or invalid. |
| **`token delete <platform>`** | Removes the stored token from the keychain for that platform. |
| **`changes fetch <platform\|all>`** | Fetches changelog/feed data for the platform(s) and stores events in the local SQLite cache. |
| **`report <platform\|all>`** | Generates Markdown and JSON reports from cached events (and token metadata where applicable) into the config reports directory. |
| **`calendar export <platform\|all> [-o FILE]`** | Exports an ICS file with events (sunsets, deadlines, maintenance, token expiry). Default file: `token-doctor.ics`; use `-o FILE` to override. |
| **`doctor run <platform\|all>`** | One-shot: runs token check, changes fetch, report, and calendar export for the platform(s). |
| **`safe-share <platform> [-o PATH]`** | Exports a sanitized diagnostics bundle (no secrets) for sharing or support; path defaults to `token-doctor-safe-share`. |

**Global flags:**

- **`--offline`** — Disable all network requests (use cached data only).
- **`--explain`** — Print the plugin manifest: endpoints, monitored sources, and what data is collected.

---

## Requirements

- **Python 3.10+** (3.12 recommended)
- **Poetry** is optional; the lockfile is committed for reproducible installs, but you can use `pip install -e .` and run tests with the same Python.

---

## Architecture (for contributors and integrators)

- **`token_doctor/core/`** — Config, secrets (keychain + encrypted fallback), redaction, HTTP client, schema, reporting, ICS calendar, plugin loader, SQLite cache.
- **`token_doctor/platforms/`** — 50+ platform plugins. Each exposes `metadata`, `token_checks()`, `collect_changes()`, and optionally `collect_status()`.
- **`token_doctor/cli/`** — Typer CLI and subcommands.
- **Database** — SQLite `cache.sqlite` under the config dir stores fetched events and timestamps.

Tokens are stored in the OS keychain (macOS Keychain, Windows Credential Manager, or Linux Secret Service). An encrypted file fallback is used only if the keychain is unavailable (with a warning).

---

## Supported platforms (50+)

| Platform | Token check | Changelog / feeds |
|----------|-------------|-------------------|
| **acxiom** | (skipped in MVP) | — |
| **adobe** | IMS userinfo | Developer blog |
| **amazon** | Ads API `/v2/profiles` | AWS/Ads blog |
| **apple_search_ads** | Bearer JWT `/api/v5/acls` | — |
| **atlassian** | Jira `/rest/api/3/myself` (set `base_url`) | Developer blog, Confluence |
| **auth0** | `/userinfo` (set `tenant`) | Auth0 blog |
| **bing_ads** | (skipped in MVP) | Microsoft Advertising blog |
| **bitbucket** | `/2.0/user` | Blog feed |
| **box** | `/2.0/users/me` | — |
| **braze** | Bearer `{rest_url}/dashboard/data_export` (set `rest_url`) | — |
| **brevo** | `/v3/account` (api-key header) | — |
| **cloudflare** | `/client/v4/user` | Blog RSS |
| **cm360** | DFA userprofiles | Release notes |
| **criteo** | (skipped in MVP) | — |
| **digitalocean** | `/v2/account` | Community & product blog |
| **discord** | `/users/@me` | Blog, developer |
| **dropbox** | `/2/users/get_current_account` | Blog feed |
| **dv360** | Bid Manager queries | Release notes |
| **github** | `/user` | Changelog RSS |
| **gitlab** | `/api/v4/user` | About & blog |
| **google_ads** | — | Release notes, blog |
| **heroku** | `/account` | Blog feed |
| **hubspot** | Bearer `/account-info/v3/details` | — |
| **instagram** | Graph `/me` | Meta blog |
| **iterable** | `/api/campaigns` (Api-Key header) | — |
| **klaviyo** | `/api/lists` (Klaviyo-API-Key) | — |
| **linear** | GraphQL `viewer` | Blog feed |
| **linkedin** | `/v2/me` | Developer feed |
| **mailchimp** | `/{dc}/3.0/ping` (Basic or Bearer; set `dc`) | — |
| **meta_marketing** | Graph `me` | Developers blog |
| **meta_messenger** | Graph `me` | Meta blog |
| **microsoft** | Graph `/v1.0/me` | M365/Graph blog |
| **netlify** | `/api/v1/user` | Blog feed |
| **notion** | `/v1/users/me` | — |
| **pinterest** | `/v5/user_account` | Developer blog |
| **quora** | (skipped in MVP) | — |
| **reddit** | oauth.reddit.com `/api/v1/me` | r/redditdev |
| **sa360** | listAccessibleCustomers | Release notes |
| **salesforce** | `{instance_url}/services/oauth2/userinfo` (set `instance_url`) | — |
| **segment** | Bearer `/workspaces` | — |
| **sendgrid** | `/v3/user/account` | Blog feed |
| **sharepoint** | Graph `/sites/root` | M365 blog |
| **slack** | `auth.test` | Changelog |
| **snapchat** | Business API `/v1/me` | — |
| **stripe** | `/v1/account` | Docs changelog |
| **taboola** | (skipped in MVP) | — |
| **the_trade_desk** | (skipped in MVP) | — |
| **tiktok** | Business user/info | — |
| **twilio** | Accounts (Basic auth) | Blog feed |
| **twitter** | API v2 `/users/me` | Developer blog |
| **vercel** | `/v2/user` | Blog, changelog |
| **verizon** | (skipped in MVP) | — |
| **whatsapp** | Graph `me` | Meta blog |
| **yahoo** | Yahoo Ads metadata | — |
| **zoom** | `/v2/users/me` | Developer blog |

Details per platform (endpoints, feeds): [docs/sources.md](docs/sources.md).

---

## Testing

**With Poetry:**

```bash
poetry install
poetry run pytest tests -v
poetry run ruff check token_doctor tests
poetry run mypy token_doctor
```

**Without Poetry** (use the same Python that has the project installed):

```bash
pip install -e ".[dev]"
pytest tests -v
python -m ruff check token_doctor tests
python -m mypy token_doctor
```

Tests cover plugin discovery, URL validity, smoke tests for every plugin, and **live link tests** that hit real docs/feeds/endpoints (run with network). CI runs the full suite on every push and PR.

---

## Documentation

- [SECURITY.md](SECURITY.md) — Threat model, token handling, redaction.
- [CONTRIBUTING.md](CONTRIBUTING.md) — **We welcome contributions.** How to add plugins, run checks, and submit changes.
- [docs/sources.md](docs/sources.md) — Monitored sources per platform.

---

## License

MIT
