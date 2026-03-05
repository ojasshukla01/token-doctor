"""
Typer CLI entrypoint.

All commands validate inputs where applicable and catch TokenDoctorError
to show user-friendly messages. Tokens are never echoed or logged.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any, TypeVar

import typer

from token_doctor.cli.ux import (
    echo_next_step_init,
    echo_next_step_token_check_failed,
    get_platform_hint,
    suggest_platform,
    try_rich_table,
)
from token_doctor.core.config import (
    TokenDoctorConfig,
    ensure_config_dir,
    load_config,
    save_config,
)
from token_doctor.core.exceptions import TokenDoctorError
from token_doctor.core.plugin_loader import (
    get_all_plugins,
    get_plugin_metadata,
    list_platform_names,
)
from token_doctor.core.redaction import redact_string
from token_doctor.core.validation import validate_platform_name

app = typer.Typer(
    name="token-doctor",
    help="Debug API tokens, track platform changes, generate calendar alerts.",
    no_args_is_help=True,
)

GLOBAL_OFFLINE = False
GLOBAL_EXPLAIN = False


F = TypeVar("F", bound=Callable[..., Any])


def _handle_errors(fn: F) -> F:
    """Decorator: catch TokenDoctorError and exit with redacted message."""
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return fn(*args, **kwargs)
        except TokenDoctorError as e:
            typer.echo(redact_string(e.message), err=True)
            raise typer.Exit(1)
    return wrapper  # type: ignore[return-value]


def _config_callback(
    ctx: typer.Context,
    offline: bool = False,
    explain: bool = False,
) -> None:
    global GLOBAL_OFFLINE, GLOBAL_EXPLAIN
    GLOBAL_OFFLINE = offline
    GLOBAL_EXPLAIN = explain


@app.callback()
def main(
    ctx: typer.Context,
    offline: Annotated[
        bool,
        typer.Option("--offline", help="Do not perform network requests."),
    ] = False,
    explain: Annotated[
        bool,
        typer.Option("--explain", help="Show plugin manifest (endpoints, sources, data collected)."),
    ] = False,
) -> None:
    _config_callback(ctx, offline, explain)


# --- ui (interactive TUI) ---
@app.command()
def ui() -> None:
    """Launch interactive menu: run all commands (status, profiles, tokens, fetch, report, etc.) from one place."""
    from token_doctor.cli.tui import run_tui

    run_tui(app)


# --- init ---
@app.command()
def init(
    config_dir: Annotated[
        Path | None,
        typer.Option("--config-dir", help="Config directory (default: ~/.config/token-doctor)"),
    ] = None,
) -> None:
    """Create config directory, initialize SQLite database, generate sample config."""
    from token_doctor.core.cache import init_db

    dir_path = config_dir or Path.home() / ".config" / "token-doctor"
    config = TokenDoctorConfig(config_dir=dir_path)
    ensure_config_dir(config)
    init_db(config.effective_db_path)
    save_config(config)
    sample = config.config_dir / "config.sample.json"
    sample.write_text(
        '{"config_dir": "' + str(config.config_dir) + '", "profiles": [], "offline": false}',
        encoding="utf-8",
    )
    typer.echo(f"Initialized config at {config.config_dir}")
    typer.echo(f"Database at {config.effective_db_path}")
    echo_next_step_init()


def _get_config() -> TokenDoctorConfig:
    """Load config; ensure config_dir exists for commands that need it."""
    try:
        return load_config()
    except Exception as e:
        typer.echo(redact_string(f"Failed to load config: {e}"), err=True)
        raise typer.Exit(1)


def _get_plugins(platforms: list[str] | None = None) -> dict[str, Any]:
    """Load plugins. If platforms is given, only those are loaded (lazy)."""
    return get_all_plugins(only_platforms=platforms)


# --- profile ---
profile_app = typer.Typer(help="Manage platform profiles.")
app.add_typer(profile_app, name="profile")


@profile_app.command("add")
def profile_add(
    platform: Annotated[str, typer.Argument(help="Platform name (e.g. github, slack).")],
) -> None:
    """Add a platform profile."""
    try:
        platform = validate_platform_name(platform)
    except TokenDoctorError as e:
        typer.echo(redact_string(e.message), err=True)
        raise typer.Exit(1)
    config = _get_config()
    plugins = _get_plugins()
    if platform not in plugins:
        available = list_platform_names()
        suggestion = suggest_platform(platform, available)
        if suggestion:
            typer.echo(f"Unknown platform: {platform}. Did you mean: {suggestion}?", err=True)
        else:
            typer.echo(f"Unknown platform: {platform}. Available: {', '.join(available)}", err=True)
        raise typer.Exit(1)
    config.add_profile(platform)
    save_config(config)
    typer.echo(f"Added profile: {platform}")
    hint = get_platform_hint(platform)
    if hint:
        typer.echo(f"Tip: {hint}")


@profile_app.command("list")
def profile_list() -> None:
    """List configured platform profiles."""
    config = _get_config()
    if not config.profiles:
        typer.echo("No profiles configured. Use: token-doctor profile add <platform>")
        return
    rows = [[p.platform, "yes" if p.enabled else "no"] for p in config.profiles]
    if not try_rich_table(["Platform", "Enabled"], rows):
        for p in config.profiles:
            typer.echo(f"  {p.platform} (enabled={p.enabled})")


@profile_app.command("remove")
def profile_remove(
    platform: Annotated[str, typer.Argument(help="Platform to remove.")],
) -> None:
    """Remove a platform profile."""
    config = _get_config()
    config.remove_profile(platform)
    save_config(config)
    typer.echo(f"Removed profile: {platform}")


# --- token ---
token_app = typer.Typer(help="Manage tokens (stored in OS keychain).")
app.add_typer(token_app, name="token")


@token_app.command("set")
def token_set(
    platform: Annotated[str, typer.Argument(help="Platform name.")],
    env: Annotated[
        str | None,
        typer.Option("--env", "-e", help="Read token from this environment variable (e.g. GITHUB_TOKEN)."),
    ] = None,
) -> None:
    """Store token in keychain (prompted interactively or from --env)."""
    import os

    from token_doctor.core.secrets import set_token
    from token_doctor.core.validation import validate_token_not_empty

    try:
        platform = validate_platform_name(platform)
    except TokenDoctorError as e:
        typer.echo(redact_string(e.message), err=True)
        raise typer.Exit(1)
    config = _get_config()
    ensure_config_dir(config)
    if env:
        raw = os.environ.get(env)
        if not raw:
            typer.echo(f"Environment variable {env} is not set or empty.", err=True)
            raise typer.Exit(1)
    else:
        typer.echo("Paste your token (input is hidden for security):", err=True)
        raw = typer.prompt("Token", hide_input=True)
        if not raw:
            typer.echo("Aborted.")
            raise typer.Exit(1)
    try:
        raw = validate_token_not_empty(raw)
    except TokenDoctorError as e:
        typer.echo(redact_string(e.message), err=True)
        raise typer.Exit(1)
    set_token(platform, raw, config.config_dir)
    typer.echo("Token stored.")


@token_app.command("info")
def token_info(
    platform: Annotated[str, typer.Argument(help="Platform name.")],
) -> None:
    """Show token metadata only (exists, last 4 chars, fingerprint, type, expiry if known)."""
    from token_doctor.core.jwt_utils import get_jwt_expiry
    from token_doctor.core.redaction import is_likely_jwt
    from token_doctor.core.secrets import get_token, token_fingerprint, token_last_four

    config = _get_config()
    tok = get_token(platform, config.config_dir)
    if not tok:
        typer.echo("No token stored for this platform.")
        return
    rows = [
        ["Property", "Value"],
        ["Token exists", "yes"],
        ["Fingerprint", token_fingerprint(tok)],
        ["Last 4", token_last_four(tok)],
        ["Detected type", "JWT" if is_likely_jwt(tok) else "API key / opaque"],
    ]
    expiry = get_jwt_expiry(tok)
    if expiry:
        rows.append(["Expiry (from JWT)", expiry.isoformat()])
    else:
        rows.append(["Expiry", "not derivable locally"])
    if not try_rich_table(["Property", "Value"], [[r[0], r[1]] for r in rows[1:]]):
        for r in rows[1:]:
            typer.echo(f"{r[0]}: {r[1]}")


@token_app.command("delete")
def token_delete(
    platform: Annotated[str, typer.Argument(help="Platform name.")],
) -> None:
    """Remove token from keychain."""
    from token_doctor.core.secrets import delete_token

    config = _get_config()
    delete_token(platform, config.config_dir)
    typer.echo("Token deleted.")


@token_app.command("check")
def token_check(
    platform: Annotated[str, typer.Argument(help="Platform name.")],
) -> None:
    """Run plugin token validation checks. Output is always redacted."""
    from token_doctor.core.jwt_utils import get_jwt_expiry
    from token_doctor.core.redaction import is_likely_jwt, redact_dict, redact_string
    from token_doctor.core.schema import CheckStatus
    from token_doctor.core.secrets import get_token

    config = _get_config()
    plugins = _get_plugins([platform])
    if platform not in plugins:
        available = list_platform_names()
        suggestion = suggest_platform(platform, available)
        if suggestion:
            typer.echo(f"Unknown platform: {platform}. Did you mean: {suggestion}?", err=True)
        else:
            typer.echo(f"Unknown platform: {platform}", err=True)
        raise typer.Exit(1)
    tok = get_token(platform, config.config_dir)
    if not tok:
        typer.echo("No token set. Use: token-doctor token set <platform>")
        echo_next_step_token_check_failed(platform)
        raise typer.Exit(1)
    plug = plugins[platform]
    results = plug.token_checks(tok, config)
    for r in results:
        msg = redact_string(r.message)
        typer.echo(f"  [{r.status.value}] {r.name}: {msg}")
        if r.details:
            typer.echo("    details: " + redact_string(str(redact_dict(r.details))))
    all_ok = all(r.status == CheckStatus.OK for r in results) if results else False
    if results and not all_ok:
        echo_next_step_token_check_failed(platform)
    # Security hints
    if tok and is_likely_jwt(tok) and get_jwt_expiry(tok) is None:
        typer.echo("  Tip: Token has no expiry in JWT; consider rotating periodically.")


# --- changes ---
changes_app = typer.Typer(help="Fetch platform change feeds.")
app.add_typer(changes_app, name="changes")


def _fetch_one_platform(
    platform: str,
    plugins: dict[str, Any],
    db_path: Path,
) -> tuple[str, list[Any]]:
    """Fetch changes for one platform. Returns (platform, events)."""
    from datetime import datetime, timedelta, timezone

    from token_doctor.core.cache import get_last_fetch
    since = get_last_fetch(db_path, platform)
    if not since:
        since = datetime.now(timezone.utc) - timedelta(days=365)
    plug = plugins.get(platform)
    if not plug:
        return platform, []
    events = plug.collect_changes(since)
    return platform, events


@changes_app.command("fetch")
def changes_fetch(
    platform: Annotated[str, typer.Argument(help="Platform name or 'all'.")],
) -> None:
    """Fetch change feeds and store in SQLite cache."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from datetime import datetime, timedelta, timezone

    from token_doctor.core.cache import get_last_fetch, init_db, upsert_events

    global GLOBAL_OFFLINE
    if GLOBAL_OFFLINE:
        typer.echo("Offline mode: skipping fetch.")
        return
    config = _get_config()
    init_db(config.effective_db_path)
    targets = list(get_all_plugins().keys()) if platform == "all" else [platform]
    plugins = _get_plugins(targets)
    if platform == "all" and len(targets) > 1:
        total = len(targets)
        completed = 0
        with ThreadPoolExecutor(max_workers=min(8, total)) as executor:
            futures = {
                executor.submit(_fetch_one_platform, p, plugins, config.effective_db_path): p
                for p in targets
                if p in plugins
            }
            for fut in as_completed(futures):
                completed += 1
                p = futures[fut]
                typer.echo(f"  Fetching {completed}/{total}: {p}...")
                try:
                    _p, events = fut.result()
                    n = upsert_events(config.effective_db_path, events)
                    typer.echo(f"  {_p}: stored {n} events.")
                except Exception as e:
                    typer.echo(f"  {p}: error - {redact_string(str(e))}", err=True)
    else:
        for p in targets:
            if p not in plugins:
                suggestion = suggest_platform(p, list_platform_names())
                typer.echo(f"Unknown platform: {p}. Did you mean: {suggestion}?" if suggestion else f"Unknown platform: {p}", err=True)
                continue
            typer.echo(f"  Fetching {p}...", err=True)
            since = get_last_fetch(config.effective_db_path, p)
            if not since:
                since = datetime.now(timezone.utc) - timedelta(days=365)
            try:
                events = plugins[p].collect_changes(since)
                n = upsert_events(config.effective_db_path, events)
                typer.echo(f"  {p}: stored {n} events.")
            except Exception as e:
                typer.echo(f"  {p}: error - {redact_string(str(e))}", err=True)


# --- report ---
@app.command()
def report(
    platform: Annotated[str, typer.Argument(help="Platform or 'all'.")],
    output_dir: Annotated[
        Path | None,
        typer.Option("--output-dir", "-o", help="Output directory for reports."),
    ] = None,
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format: md, json, or html (single file)."),
    ] = "md",
) -> None:
    """Generate Markdown, JSON, and/or HTML report."""
    from datetime import datetime, timezone

    from token_doctor.core.cache import get_events, init_db
    from token_doctor.core.jwt_utils import get_jwt_expiry
    from token_doctor.core.reporting import report_to_html, write_reports
    from token_doctor.core.schema import PlatformReport
    from token_doctor.core.secrets import get_token

    config = _get_config()
    init_db(config.effective_db_path)
    targets = list(get_all_plugins().keys()) if platform == "all" else [platform]
    plugins = _get_plugins(targets)
    out_dir = output_dir or config.config_dir / "reports"
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for p in targets:
        if p not in plugins:
            continue
        events = get_events(config.effective_db_path, platform=p)
        tok = get_token(p, config.config_dir)
        token_metadata: dict[str, Any] = {}
        if tok:
            from token_doctor.core.secrets import token_fingerprint, token_last_four
            token_metadata["fingerprint"] = token_fingerprint(tok)
            token_metadata["last_four"] = token_last_four(tok)
            exp = get_jwt_expiry(tok)
            if exp:
                token_metadata["expires_at"] = exp.isoformat()
        token_checks = []
        if tok and not GLOBAL_OFFLINE:
            token_checks = plugins[p].token_checks(tok, config)
        report_obj = PlatformReport(
            platform=p,
            generated_at=datetime.now(timezone.utc),
            events=events,
            token_checks=token_checks,
            token_metadata=token_metadata,
        )
        if format == "html":
            html_path = out_dir / f"{p}.html"
            html_path.write_text(report_to_html(report_obj), encoding="utf-8")
            typer.echo(f"  {p}: {html_path}")
        else:
            md_path, json_path = write_reports(report_obj, out_dir)
            typer.echo(f"  {p}: {md_path}, {json_path}")


# --- calendar ---
calendar_app = typer.Typer(help="Export ICS calendar.")
app.add_typer(calendar_app, name="calendar")


@calendar_app.command("export")
def calendar_export(
    platform: Annotated[str, typer.Argument(help="Platform or 'all'.")],
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Output ICS file path.", default_factory=lambda: Path("token-doctor.ics")),
    ],
) -> None:
    """Export ICS for sunsets, deadlines, maintenance, token expiry."""
    from datetime import datetime, timezone

    from token_doctor.core.cache import get_events, init_db
    from token_doctor.core.calendar import export_ics
    from token_doctor.core.jwt_utils import get_jwt_expiry
    from token_doctor.core.schema import PlatformReport
    from token_doctor.core.secrets import get_token

    config = _get_config()
    init_db(config.effective_db_path)
    targets = list(get_all_plugins().keys()) if platform == "all" else [platform]
    plugins = _get_plugins(targets)
    reports = []
    for p in targets:
        if p not in plugins:
            continue
        events = get_events(config.effective_db_path, platform=p)
        tok = get_token(p, config.config_dir)
        token_metadata: dict[str, Any] = {}
        if tok:
            from token_doctor.core.secrets import token_fingerprint, token_last_four
            token_metadata["fingerprint"] = token_fingerprint(tok)
            token_metadata["last_four"] = token_last_four(tok)
            exp = get_jwt_expiry(tok)
            if exp:
                token_metadata["expires_at"] = exp
        report_obj = PlatformReport(
            platform=p,
            generated_at=datetime.now(timezone.utc),
            events=events,
            token_checks=[],
            token_metadata=token_metadata,
        )
        reports.append(report_obj)
    paths = export_ics(reports, output, combined=(platform == "all"))
    for path in paths:
        typer.echo(f"Wrote {path}")


# --- status ---
@app.command()
def status() -> None:
    """One-screen summary: token status per profile, event counts, next deadline."""
    from datetime import datetime, timezone

    from token_doctor.core.cache import get_event_counts, get_next_deadlines, init_db
    from token_doctor.core.jwt_utils import get_jwt_expiry
    from token_doctor.core.secrets import get_token

    config = _get_config()
    init_db(config.effective_db_path)
    counts = get_event_counts(config.effective_db_path)
    deadlines = get_next_deadlines(config.effective_db_path, limit=5)
    now = datetime.now(timezone.utc)
    rows = []
    for p in config.profiles:
        if not p.enabled:
            continue
        tok = get_token(p.platform, config.config_dir)
        if not tok:
            status_str = "no token"
        else:
            exp = get_jwt_expiry(tok)
            if exp:
                delta = (exp - now).days
                status_str = "ok" if delta > 7 else "expires soon" if delta > 0 else "expired"
            else:
                status_str = "ok (no expiry in JWT)"
        n = counts.get(p.platform, 0)
        rows.append([p.platform, status_str, str(n)])
    if try_rich_table(["Platform", "Token", "Events"], rows):
        pass
    else:
        for r in rows:
            typer.echo(f"  {r[0]}: {r[1]} | {r[2]} events")
    if deadlines:
        typer.echo("")
        typer.echo("Next deadlines:")
        for e in deadlines:
            ed = e.effective_date.date().isoformat() if e.effective_date else ""
            typer.echo(f"  {ed} [{e.platform}] {e.title[:50]}")

# --- dashboard ---
@app.command()
def dashboard() -> None:
    """Status plus recent changelog (mini status page)."""
    from datetime import datetime, timezone
    status()
    from token_doctor.core.cache import get_events, init_db
    config = _get_config()
    init_db(config.effective_db_path)
    all_events: list[Any] = []
    min_dt = datetime(1970, 1, 1, tzinfo=timezone.utc)
    for p in config.profiles:
        if not p.enabled:
            continue
        events = get_events(config.effective_db_path, platform=p.platform)
        for e in events:
            all_events.append((e.platform, e))
    all_events.sort(key=lambda x: (x[1].published_at or x[1].effective_date or min_dt), reverse=True)
    typer.echo("")
    typer.echo("Recent events (last 5):")
    for platform, e in all_events[:5]:
        pub = (e.published_at or e.effective_date)
        pub_str = pub.isoformat()[:10] if pub else ""
        typer.echo(f"  [{platform}] {pub_str} {e.title[:60]}")

# --- expiring ---
@app.command()
def expiring(
    days: Annotated[int, typer.Option("--days", "-d", help="Warn if token expires within this many days.")] = 7,
) -> None:
    """List tokens that expire within the given days."""
    from datetime import datetime, timezone

    from token_doctor.core.jwt_utils import get_jwt_expiry
    from token_doctor.core.secrets import get_token

    config = _get_config()
    now = datetime.now(timezone.utc)
    found = []
    for p in config.profiles:
        if not p.enabled:
            continue
        tok = get_token(p.platform, config.config_dir)
        if not tok:
            continue
        exp = get_jwt_expiry(tok)
        if not exp:
            continue
        delta = (exp - now).days
        if delta <= days:
            found.append((p.platform, exp, delta))
    if not found:
        typer.echo(f"No tokens expiring within {days} days.")
        return
    for platform, exp, delta in found:
        typer.echo(f"  {platform}: expires {exp.date().isoformat()} (in {delta} days)")

# --- doctor run ---
doctor_app = typer.Typer(help="One-shot run: token check, fetch changes, report, calendar.")
app.add_typer(doctor_app, name="doctor")


@doctor_app.command("run")
def doctor_run(
    platform: Annotated[str, typer.Argument(help="Platform or 'all'.")],
    ci: Annotated[bool, typer.Option("--ci", help="Exit 2 if any token invalid or critical sunset < 30 days.")] = False,
    watch: Annotated[
        int | None,
        typer.Option("--watch", "-w", help="Run repeatedly every N seconds (e.g. 3600 for hourly)."),
    ] = None,
    notify: Annotated[bool, typer.Option("--notify", help="Echo alerts for expiring tokens or critical events.")] = False,
) -> None:
    """Run token check, changes fetch, report generation, calendar export."""
    import time
    from datetime import datetime, timezone

    from token_doctor.core.cache import get_next_deadlines, init_db
    from token_doctor.core.schema import EventType

    def run_once() -> bool:
        targets = list(get_all_plugins().keys()) if platform == "all" else [platform]
        plugins = _get_plugins(targets)
        for p in targets:
            if p in plugins:
                token_check(p)
        changes_fetch(platform)
        report(platform)
        calendar_export(platform, Path("token-doctor.ics"))
        if ci:
            config = _get_config()
            init_db(config.effective_db_path)
            # Check: any token invalid (we cannot re-run checks here without token) - skip; or critical event
            deadlines = get_next_deadlines(config.effective_db_path, limit=50)
            for e in deadlines:
                if e.effective_date and e.event_type in (EventType.SUNSET, EventType.DEPRECATION):
                    delta = (e.effective_date - datetime.now(timezone.utc)).days
                    if 0 <= delta <= 30:
                        typer.echo(f"CI: critical event within 30 days: {e.platform} {e.title}", err=True)
                        raise typer.Exit(2)
        if notify:
            from token_doctor.core.jwt_utils import get_jwt_expiry
            from token_doctor.core.secrets import get_token
            config = _get_config()
            for profile in config.profiles:
                if not profile.enabled:
                    continue
                tok = get_token(profile.platform, config.config_dir)
                if tok:
                    exp = get_jwt_expiry(tok)
                    if exp and (exp - datetime.now(timezone.utc)).days <= 7:
                        typer.echo(f"ALERT: token {profile.platform} expires within 7 days.")
            deadlines = get_next_deadlines(config.effective_db_path, limit=5)
            for e in deadlines:
                if e.effective_date and e.event_type in (EventType.SUNSET, EventType.DEPRECATION):
                    delta = (e.effective_date - datetime.now(timezone.utc)).days
                    if 0 <= delta <= 30:
                        typer.echo(f"ALERT: {e.platform} - {e.title} (in {delta} days)")
        return True

    if watch is not None:
        if watch < 60:
            typer.echo("--watch must be at least 60 seconds.", err=True)
            raise typer.Exit(1)
        while True:
            run_once()
            typer.echo(f"Next run in {watch}s...")
            time.sleep(watch)
    else:
        run_once()


# --- safe-share ---
@app.command()
def safe_share(
    platform: Annotated[str, typer.Argument(help="Platform name.")],
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Output bundle path (directory or zip).", default_factory=lambda: Path("token-doctor-safe-share")),
    ],
) -> None:
    """Export sanitized diagnostics bundle (no secrets)."""
    import json
    from datetime import datetime, timezone

    from token_doctor.core.cache import get_events, init_db
    from token_doctor.core.redaction import redact_dict

    config = _get_config()
    init_db(config.effective_db_path)
    plugins = _get_plugins()
    if platform not in plugins:
        available = list_platform_names()
        suggestion = suggest_platform(platform, available)
        if suggestion:
            typer.echo(f"Unknown platform: {platform}. Did you mean: {suggestion}?", err=True)
        else:
            typer.echo(f"Unknown platform: {platform}", err=True)
        raise typer.Exit(1)
    meta = get_plugin_metadata(plugins[platform])
    events = get_events(config.effective_db_path, platform=platform)
    config_safe = {
        "config_dir": str(config.config_dir),
        "db_path": str(config.effective_db_path),
        "profiles": [{"platform": p.platform, "enabled": p.enabled} for p in config.profiles],
        "no_secrets": True,
    }
    bundle = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "platform": platform,
        "config": config_safe,
        "plugin_metadata": meta,
        "events_count": len(events),
        "events": [
            {
                "event_type": e.event_type.value,
                "title": e.title,
                "effective_date": e.effective_date.isoformat() if e.effective_date else None,
                "raw_id": e.raw_id,
            }
            for e in events
        ],
    }
    out_path = Path(output)
    if out_path.suffix.lower() == ".json":
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(redact_dict(bundle), indent=2), encoding="utf-8")
        typer.echo(f"Safe-share bundle written to {out_path}")
    else:
        out_path.mkdir(parents=True, exist_ok=True)
        out_path = out_path / "safe-share.json"
        out_path.write_text(json.dumps(redact_dict(bundle), indent=2), encoding="utf-8")
        typer.echo(f"Safe-share bundle written to {out_path}")


# --- explain (--explain) ---
def _maybe_explain(platform: str | None) -> None:
    if not GLOBAL_EXPLAIN:
        return
    plugins = _get_plugins()
    for name, plug in (plugins.items() if platform is None else [(platform, plugins.get(platform))]):
        if plug is None:
            continue
        meta = get_plugin_metadata(plug)
        typer.echo(f"Plugin: {meta.get('platform', name)}")
        typer.echo(f"  Endpoints: {meta.get('declared_endpoints', [])}")
        typer.echo(f"  Sources: {meta.get('sources_monitored', [])}")
        typer.echo(f"  Data collected: {meta.get('data_collected', [])}")


if __name__ == "__main__":
    app()
