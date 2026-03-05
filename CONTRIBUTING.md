# Contributing to token-doctor

We welcome contributions. This file explains how to add new platforms and what to keep in sync.

---

## Adding a new platform (or plugin)

When you add a new platform plugin, update **all** of the following so the app and tests stay consistent. If you miss one, CI or local tests will fail (by design).

### 1. Plugin implementation

- Add the platform under **`token_doctor/platforms/`** (or register it via the `token_doctor.plugins` entry point in `pyproject.toml`).
- Implement the plugin interface: `metadata`, `token_checks()`, `collect_changes()`, and optionally `collect_status()`.

### 2. Expected platforms list (tests)

- **File:** `tests/test_plugin_loader.py`
- **Update:** Add the new platform name to the **`EXPECTED_PLATFORMS`** list.
- **Why:** Ensures the plugin is discovered and counted in CI.

### 3. Platform hints (CLI UX)

- **File:** `token_doctor/cli/ux.py`
- **Update:** Add an entry for the new platform to **`PLATFORM_HINTS`**.
- **Why:** After `profile add <platform>`, the CLI prints a one-line tip (e.g. “Set 'tenant' in profile options for Auth0” or “Store your token with: token-doctor token set &lt;platform&gt;.”). If the platform is missing from `PLATFORM_HINTS`, **`test_platform_hints_cover_all_plugins`** (in `tests/test_new_features.py`) will fail until you add it.
- **Options:** Use a custom hint if the platform needs profile options (e.g. `tenant`, `base_url`, `instance_url`); otherwise use the generic: `"Store your token with: token-doctor token set {platform}."`

### 4. Documentation

- **`README.md`** — Add the platform to the “Supported platforms (50+)” table (token check and changelog/feeds columns).
- **`docs/sources.md`** — Add a section for the new platform with token validation endpoint(s) and monitored feeds, following the existing format.

### 5. Run checks

After making changes:

```bash
poetry run pytest tests -v
poetry run ruff check token_doctor tests
poetry run mypy token_doctor
```

If you add a platform but forget to add it to **`PLATFORM_HINTS`**, the test **`test_platform_hints_cover_all_plugins`** will fail and remind you. Use that (and the list above) as a checklist for every new platform or plugin.

---

## Other ways to contribute

- Run tests and fix failures, improve test coverage.
- Improve docs (TROUBLESHOOTING, sources, inline comments).
- Report issues and suggest features (see SECURITY.md for sensitive reports).

Thanks for contributing.
