# Security

## Threat model

- **Local-first:** No remote server; all logic runs on the user’s machine.
- **Token handling:** Tokens are used only to call declared platform APIs (e.g. GitHub `/user`) and to derive metadata (e.g. JWT expiry). They are never sent to any token-doctor backend (there is none).
- **Assumptions:** The OS keychain and keyring backend are trusted. Network and platform APIs are assumed hostile (TLS, no token in URLs).

## Token handling rules

1. **Storage:** Tokens are stored only in the OS keychain via the `keyring` library (Keychain on macOS, Windows Credential Manager, Secret Service on Linux).
2. **Fallback:** If the keychain is unavailable, an encrypted file fallback may be used; the user is warned. The fallback key is derived from `TOKEN_DOCTOR_FALLBACK_KEY` or a machine-specific path. Do not rely on it for high-security environments.
3. **No token in output:** Tokens must never be printed in CLI output, logs, or reports. Only metadata (existence, fingerprint, last 4 chars, expiry when derivable) may be shown.
4. **No token in URLs:** Tokens are sent only in `Authorization` headers, never as query or form parameters.

## Redaction guarantees

- **redaction** module: All CLI output and exception messages that might contain user input or API responses are passed through redaction. Patterns: JWTs, Bearer tokens, GitHub-style PATs, long opaque tokens. Secret-like dict keys (e.g. `token`, `password`, `api_key`) are always replaced with a placeholder in serialized output.
- **Safe-share:** The `safe-share` command exports only config (no secrets), plugin metadata, and event cache; no token or key material.
- **Interactive UI:** The `ui` command runs the same CLI subcommands (e.g. `token set`, `token check`) via the same code paths; token handling and storage are unchanged. No tokens are logged or displayed in the TUI. The **tui** command (Textual dashboard) uses the same CLI and core APIs; tokens are not shown or logged there either.

## Pre-commit

Pre-commit hooks are configured to reduce the risk of committing tokens (e.g. detect-secrets, pattern-based checks). Run `pre-commit install` and fix any reported issues before committing.

## Reporting issues

Please report security-sensitive bugs privately (e.g. via maintainer contact or security policy) rather than in public issues.
