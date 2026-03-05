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

### 5. Interactive TUI (optional)

- **`token_doctor/cli/tui.py`** — The `token-doctor ui` command uses this. If you add a new CLI feature that should appear in the interactive menu, add a corresponding option in `run_tui()` (main menu or submenus). The TUI invokes the same CLI via `CliRunner`, so no duplicate logic.

- **`token_doctor/cli/textual_app.py`** — The **Textual TUI** (`token-doctor tui`) uses this. It shows a dashboard (status table, alerts, next deadlines, recent events with sunset/deprecation/version tags), main menu (same options as `ui` plus **11. All events**), and an All events screen (key **v** from dashboard). Event list shows sunset/deprecation deadlines and version_upgrade/breaking_change tags. All `textual` imports stay in this module so the rest of the project runs without Textual. Optional dependency: install with `pip install -e '.[textual]'`.

### 6. Run checks

After making changes:

```bash
poetry run pytest tests -v
poetry run ruff check token_doctor tests
poetry run mypy token_doctor
```

Optional: run `token-doctor ui` and test the new flow from the menu.

If you add a platform but forget to add it to **`PLATFORM_HINTS`**, the test **`test_platform_hints_cover_all_plugins`** will fail and remind you. Use that (and the list above) as a checklist for every new platform or plugin.

---

## Other ways to contribute

- Run tests and fix failures, improve test coverage.
- Improve docs (TROUBLESHOOTING, sources, inline comments).
- Report issues and suggest features (see SECURITY.md for sensitive reports).

Thanks for contributing.
