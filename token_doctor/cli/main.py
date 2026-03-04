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

from token_doctor.core.config import (
    TokenDoctorConfig,
    ensure_config_dir,
    load_config,
    save_config,
)
from token_doctor.core.exceptions import TokenDoctorError
from token_doctor.core.plugin_loader import get_all_plugins, get_plugin_metadata
from token_doctor.core.redaction import redact_string
from token_doctor.core.validation import validate_platform_name

app = typer.Typer(
    name="token-doctor",
    help="Debug API tokens, track platform changes, generate calendar alerts.",
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


def _get_config() -> TokenDoctorConfig:
    """Load config; ensure config_dir exists for commands that need it."""
    try:
        return load_config()
    except Exception as e:
        typer.echo(redact_string(f"Failed to load config: {e}"), err=True)
        raise typer.Exit(1)


def _get_plugins() -> dict[str, Any]:
    return get_all_plugins()


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
        available = ", ".join(sorted(plugins.keys()))
        typer.echo(f"Unknown platform: {platform}. Available: {available}", err=True)
        raise typer.Exit(1)
    config.add_profile(platform)
    save_config(config)
    typer.echo(f"Added profile: {platform}")


@profile_app.command("list")
def profile_list() -> None:
    """List configured platform profiles."""
    config = _get_config()
    if not config.profiles:
        typer.echo("No profiles configured. Use: token-doctor profile add <platform>")
        return
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
) -> None:
    """Store token in keychain (prompted interactively)."""
    from token_doctor.core.secrets import set_token
    from token_doctor.core.validation import validate_token_not_empty

    try:
        platform = validate_platform_name(platform)
    except TokenDoctorError as e:
        typer.echo(redact_string(e.message), err=True)
        raise typer.Exit(1)
    config = _get_config()
    ensure_config_dir(config)
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
    typer.echo("Token exists: yes")
    typer.echo(f"Fingerprint: {token_fingerprint(tok)}")
    typer.echo(f"Last 4: {token_last_four(tok)}")
    typer.echo("Detected type: JWT" if is_likely_jwt(tok) else "Detected type: API key / opaque")
    expiry = get_jwt_expiry(tok)
    if expiry:
        typer.echo(f"Expiry (from JWT): {expiry.isoformat()}")
    else:
        typer.echo("Expiry: not derivable locally")


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
    from token_doctor.core.redaction import redact_dict, redact_string
    from token_doctor.core.secrets import get_token

    config = _get_config()
    plugins = _get_plugins()
    if platform not in plugins:
        typer.echo(f"Unknown platform: {platform}")
        raise typer.Exit(1)
    tok = get_token(platform, config.config_dir)
    if not tok:
        typer.echo("No token set. Use: token-doctor token set <platform>")
        raise typer.Exit(1)
    plug = plugins[platform]
    results = plug.token_checks(tok, config)
    for r in results:
        msg = redact_string(r.message)
        typer.echo(f"  [{r.status.value}] {r.name}: {msg}")
        if r.details:
            typer.echo("    details: " + redact_string(str(redact_dict(r.details))))


# --- changes ---
changes_app = typer.Typer(help="Fetch platform change feeds.")
app.add_typer(changes_app, name="changes")


@changes_app.command("fetch")
def changes_fetch(
    platform: Annotated[str, typer.Argument(help="Platform name or 'all'.")],
) -> None:
    """Fetch change feeds and store in SQLite cache."""
    from datetime import datetime, timedelta, timezone

    from token_doctor.core.cache import get_last_fetch, init_db, upsert_events

    global GLOBAL_OFFLINE
    if GLOBAL_OFFLINE:
        typer.echo("Offline mode: skipping fetch.")
        return
    config = _get_config()
    init_db(config.effective_db_path)
    plugins = _get_plugins()
    targets = list(plugins.keys()) if platform == "all" else [platform]
    for p in targets:
        if p not in plugins:
            typer.echo(f"Unknown platform: {p}")
            continue
        since = get_last_fetch(config.effective_db_path, p)
        if not since:
            since = datetime.now(timezone.utc) - timedelta(days=365)
        events = plugins[p].collect_changes(since)
        n = upsert_events(config.effective_db_path, events)
        typer.echo(f"  {p}: stored {n} events.")


# --- report ---
@app.command()
def report(
    platform: Annotated[str, typer.Argument(help="Platform or 'all'.")],
    output_dir: Annotated[
        Path | None,
        typer.Option("--output-dir", "-o", help="Output directory for reports."),
    ] = None,
) -> None:
    """Generate Markdown and JSON report."""
    from datetime import datetime, timezone

    from token_doctor.core.cache import get_events, init_db
    from token_doctor.core.jwt_utils import get_jwt_expiry
    from token_doctor.core.reporting import write_reports
    from token_doctor.core.schema import PlatformReport
    from token_doctor.core.secrets import get_token

    config = _get_config()
    init_db(config.effective_db_path)
    plugins = _get_plugins()
    targets = list(plugins.keys()) if platform == "all" else [platform]
    out_dir = output_dir or config.config_dir / "reports"
    for p in targets:
        if p not in plugins:
            typer.echo(f"Unknown platform: {p}")
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
    plugins = _get_plugins()
    targets = list(plugins.keys()) if platform == "all" else [platform]
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


# --- doctor run ---
doctor_app = typer.Typer(help="One-shot run: token check, fetch changes, report, calendar.")
app.add_typer(doctor_app, name="doctor")


@doctor_app.command("run")
def doctor_run(
    platform: Annotated[str, typer.Argument(help="Platform or 'all'.")],
) -> None:
    """Run token check, changes fetch, report generation, calendar export."""
    plugins = _get_plugins()
    targets = list(plugins.keys()) if platform == "all" else [platform]
    for p in targets:
        if p in plugins:
            token_check(p)
    changes_fetch(platform)
    report(platform)
    calendar_export(platform, Path("token-doctor.ics"))


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
        typer.echo(f"Unknown platform: {platform}")
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
