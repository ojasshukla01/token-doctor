# Troubleshooting

Common issues and how to fix them.

---

## Keychain unavailable / Using encrypted file fallback

**Symptom:** A warning like: "Keychain unavailable. Using encrypted file fallback."

**Cause:** The OS keychain (macOS Keychain, Windows Credential Manager, or Linux Secret Service) is not available or not unlocked.

**What to do:**
- **macOS:** Log in to your user account and unlock the Keychain (e.g. Keychain Access app). If you're in a headless/CI environment, keychain may not be available; use the fallback or provide tokens via `token set --env VAR`.
- **Windows:** Ensure you're logged in. Credential Manager is usually available for the current user.
- **Linux:** Install and configure a Secret Service provider (e.g. `gnome-keyring`, `kwallet`). If none is available, token-doctor uses an encrypted file in your config directory.

Tokens in the fallback are still stored encrypted. Prefer the OS keychain when possible.

---

## Token invalid or expired

**Symptom:** `token-doctor token check <platform>` reports `[error] validity: Token invalid or expired`.

**Causes:**
- The token was revoked or has expired.
- Wrong token type (e.g. OAuth vs PAT).
- Token doesn’t have the required scopes.

**What to do:**
1. Generate a new token in the platform’s developer/settings page.
2. Run: `token-doctor token set <platform>` and paste the new token (or use `--env VAR` if reading from an environment variable).
3. Run `token-doctor token check <platform>` again.

If you use JWTs, run `token-doctor token info <platform>` to see expiry (if present in the token).

---

## Command not found: token-doctor

**Symptom:** `token-doctor` is not recognized (e.g. on Windows or when the script directory isn’t on PATH).

**What to do:**
- Run via Python module:  
  `python -m token_doctor.cli.main`
- Or add the Scripts directory to your PATH. For example, with a virtualenv it’s `<venv>/Scripts` (Windows) or `<venv>/bin` (Unix). With Windows Store Python, the installer may suggest adding a path; you can use that or the module form above.

---

## No network / Offline mode

**Symptom:** You want to run without internet (e.g. air-gapped or cached data only).

**What to do:**
- Use the global `--offline` flag:  
  `token-doctor --offline report all`  
  This skips all HTTP requests (token checks and change fetches). Reports and calendar export use only cached data.

---

## Unknown platform / Did you mean?

**Symptom:** "Unknown platform: githb" (typo).

**What to do:**
- Check the suggested platform: "Did you mean: github?"
- List available platforms: run `token-doctor profile add` and look at the error message, or check the README for the supported platforms table.
- Use the exact platform name (lowercase, e.g. `github`, `google_ads`).

---

## Certificate verify failed / SSL errors

**Symptom:** Live link tests or fetch fails with SSL/certificate errors (e.g. in CI or corporate proxy).

**What to do:**
- Ensure system CA bundle is up to date. On Linux, `update-ca-certificates` (or equivalent) may help.
- If you use a corporate proxy or custom CA, set `SSL_CERT_FILE` or `REQUESTS_CA_BUNDLE` to the correct bundle (Python/httpx respect these).
- In test runs, some external URLs may have hostname/certificate issues; those tests are skipped when the request fails with a certificate error.

---

## Tests failing locally

**Symptom:** `pytest tests` fails (e.g. import errors, missing deps).

**What to do:**
- Install in editable mode with dev deps:  
  `pip install -e ".[dev]"`  
  or with Poetry: `poetry install`
- Run from the project root so `token_doctor` and `tests` are on the path.
- Live link tests (`test_plugin_links_live.py`) need network access; some tests may be skipped on connection or certificate failure.

---

## Need more help?

- Open an issue on GitHub with the command you ran, the full error message (redact any secrets), and your OS/Python version.
- See [SECURITY.md](../SECURITY.md) for how tokens and redaction work.
- See [CONTRIBUTING.md](../CONTRIBUTING.md) for development and plugin setup.
