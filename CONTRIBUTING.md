# Contributing to token-doctor

**We actively want your help.** Whether you add a platform plugin, fix a bug, improve docs, or suggest an idea — contributions are welcome and encouraged.

This doc explains how to contribute and what we expect so your first PR is smooth.

---

## How you can contribute

- **New platform plugins** — Add support for an API or service you use (see below).
- **Bug fixes and improvements** — Open an issue or PR for bugs, UX, or performance.
- **Documentation** — Clarify README, CONTRIBUTING, or in-code comments.
- **Tests** — Add or extend tests for existing or new plugins.
- **Ideas** — Open a discussion or issue for features or design changes.

No contribution is too small. If something is unclear, say so; we’ll improve the docs and process.

---

## Steps to contribute

### 1. Get the project running locally

```bash
# Clone your fork (or the repo if you have write access)
git clone https://github.com/<your-username>/token-doctor.git
cd token-doctor

# Install in editable mode
pip install -e .
# Or with Poetry:
poetry install

# Confirm the CLI works
python -m token_doctor.cli.main --help
```

### 2. Run the test suite and checks

We ask that all PRs keep tests green and pass linting. From the project root:

```bash
# Install dev dependencies if you haven’t
pip install -e ".[dev]"

# Run tests (includes live link checks; needs network)
pytest tests -v

# Lint
python -m ruff check token_doctor tests

# Type check (optional but encouraged)
python -m mypy token_doctor
```

**CI** runs the same on every push and PR. Fix any failures before requesting review.

### 3. Make your change

- Use a **branch** (e.g. `feature/github-improvements`, `fix/calendar-export`).
- Prefer **small, focused PRs** (one feature or fix per PR when possible).
- Follow existing **code style**: Ruff, type hints, no secrets in code or logs.

### 4. Open a pull request

- **Target** the default branch (`main` or `master`).
- **Describe** what you changed and why; link any related issues.
- **Ensure** tests and Ruff pass. If CI is set up, wait for the green check.

Maintainers will review and may ask for tweaks. We’re here to get your contribution in, not to block it.

---

## Adding a new platform plugin

This is the most common type of contribution. Here’s the concrete process.

### 1. Create the plugin package

Under `token_doctor/platforms/<name>/` add:

- **`__init__.py`** — Export `plugin` (the plugin object).
- **`plugin.py`** (or your chosen module) — Define the plugin and implement the interface below.

Use a short, lowercase name (e.g. `github`, `slack`, `google_ads`). No manual registration is needed; the loader discovers any package under `platforms/` that exposes `plugin`.

### 2. Implement the plugin interface

The plugin object must provide:

**`metadata`** (dict):

- `platform`: str (e.g. `"github"`)
- `auth_types`: list[str]
- `documentation_links`: list[str] — Docs/help URLs
- `declared_endpoints`: list[str] — URLs used for token validation or API calls (can contain placeholders like `{tenant}`)
- `sources_monitored`: list[str] — Feeds/URLs used for change collection
- `data_collected`: list[str] — Short description of what data is collected

**`token_checks(token: str, config)`** → `list[CheckResult]`  
Run validation (e.g. call `/user`). Never log or echo the token.

**`collect_changes(since: datetime | None)`** → `list[NormalizedEvent]`  
Fetch changelog/feeds and return normalized events.

**`collect_status()`** → `list[NormalizedEvent] | None` (optional)  
Platform maintenance/status events, if the API provides them.

### 3. Use core helpers

- **HTTP:** `token_doctor.core.http_client.get(url, token=...)` — never log the token.
- **Schema:** `token_doctor.core.schema` — `CheckResult`, `CheckStatus`, `NormalizedEvent`, `EventType`, `ConfidenceLevel`.
- **Feeds:** Prefer **feedparser** for RSS/Atom; avoid heavy scraping unless necessary and behind an opt-in.

Set **`NormalizedEvent.confidence`** from the source:

- Official API/docs feed → `ConfidenceLevel.HIGH`
- Official vendor blog → `ConfidenceLevel.MEDIUM`
- Scraped or unofficial → `ConfidenceLevel.LOW`

### 4. Register the platform in tests

- Add your platform to **`EXPECTED_PLATFORMS`** in `tests/test_plugin_loader.py`.
- Add unit tests for schema conformance and, if possible, mocked HTTP (e.g. with `respx`). Run the full suite so URL validity and smoke tests pass.

### 5. Document sources

Update **`docs/sources.md`** with the endpoints and feeds your plugin uses so others (and CI) can verify them.

---

## Code style and quality

- **Ruff** for linting; fix any issues before submitting.
- **Type hints** and mypy-friendly code are encouraged.
- **No secrets or tokens** in code, config, or logs. Use the keychain and redaction helpers.

---

## Questions?

- Open a **GitHub issue** for bugs, feature ideas, or unclear behavior.
- Use **GitHub Discussions** (if enabled) for design or “how do I…” questions.
- In PRs, ask for help if CI or review feedback is unclear; we’re happy to clarify.

Thank you for contributing — every PR and issue makes this project better for everyone.
