"""
Interactive terminal UI: one command launches a menu to run all token-doctor features.

Run: token-doctor ui
Then use numbered menus to run status, profiles, tokens, fetch, report, calendar, etc.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from typer.testing import CliRunner


def _print(text: str = "") -> None:
    """Echo to stdout (no Rich so TUI works in minimal envs)."""
    print(text, flush=True)


def _input(prompt: str) -> str:
    """Read line from stdin."""
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        return ""


def _pause() -> None:
    _input("\nPress Enter to continue...")


def _run_cmd(runner: CliRunner, app: Any, args: list[str]) -> str:
    """Invoke CLI with args; return combined output."""
    result = runner.invoke(app, args)
    # Use .output (combined) when stderr is mixed; avoid .stderr unless separately captured
    out = getattr(result, "output", None) or result.stdout or ""
    return out.strip() if out else f"(exit code {result.exit_code})"


def _ensure_config(runner: CliRunner, app: Any) -> bool:
    """If config dir has no config.json, run init. Return True if ready."""
    config_dir = Path.home() / ".config" / "token-doctor"
    config_file = config_dir / "config.json"
    if config_file.exists():
        return True
    _print("Config not found. Running init...")
    _print(_run_cmd(runner, app, ["init"]))
    return True


def _get_profiles(runner: CliRunner, app: Any) -> list[str]:
    """Return list of configured profile platform names."""
    from token_doctor.core.config import load_config

    try:
        config = load_config()
        return [p.platform for p in config.profiles if p.enabled]
    except Exception:
        return []


def _get_available_platforms() -> list[str]:
    """Return sorted list of available platform names."""
    from token_doctor.core.plugin_loader import list_platform_names

    return list_platform_names()


def _choose_platform(
    prompt: str,
    profiles: list[str],
    allow_all: bool = False,
    allow_new: bool = False,
) -> str | None:
    """Show numbered list; return chosen platform or None to go back."""
    options = list(profiles)
    if allow_all:
        options = ["all"] + options
    if allow_new:
        available = _get_available_platforms()
        for p in available:
            if p not in options:
                options.append(p)
    if not options:
        _print("No platforms configured. Add one via Profiles > Add profile.")
        return None
    for i, name in enumerate(options, 1):
        _print(f"  {i}. {name}")
    _print("  0. Back")
    choice = _input(f"{prompt} [0-{len(options)}]: ")
    if not choice or choice == "0":
        return None
    try:
        idx = int(choice)
        if 1 <= idx <= len(options):
            return options[idx - 1]
    except ValueError:
        pass
    return None


def _main_menu() -> str:
    _print()
    _print("  ┌──────────────────────────────────────────┐")
    _print("  │         token-doctor · Main menu         │")
    _print("  ├──────────────────────────────────────────┤")
    _print("  │  1. Dashboard (status + recent events)   │")
    _print("  │  2. Status (token + event summary)       │")
    _print("  │  3. Profiles (list / add / remove)       │")
    _print("  │  4. Tokens (set / check / info / delete) │")
    _print("  │  5. Fetch changes (changelog feeds)      │")
    _print("  │  6. Report (Markdown / JSON / HTML)      │")
    _print("  │  7. Calendar export (ICS)                │")
    _print("  │  8. Expiring tokens                      │")
    _print("  │  9. Doctor run (check + fetch + report)  │")
    _print("  │ 10. Safe-share (export diagnostics)      │")
    _print("  │  0. Exit                                 │")
    _print("  └──────────────────────────────────────────┘")
    return _input("Choice [0-10]: ").strip()


def _profiles_menu(runner: CliRunner, app: Any) -> None:
    while True:
        _print("\n--- Profiles ---")
        _print("  1. List profiles")
        _print("  2. Add profile")
        _print("  3. Remove profile")
        _print("  0. Back")
        c = _input("Choice [0-3]: ").strip()
        if c == "0":
            return
        if c == "1":
            _print(_run_cmd(runner, app, ["profile", "list"]))
            _pause()
            continue
        if c == "2":
            platforms = _get_available_platforms()
            _print("Available platforms (first 20): " + ", ".join(platforms[:20]))
            if len(platforms) > 20:
                _print("  ... and more. Type a name from the list.")
            name = _input("Platform name: ").strip()
            if name:
                _print(_run_cmd(runner, app, ["profile", "add", name]))
            _pause()
            continue
        if c == "3":
            profiles = _get_profiles(runner, app)
            platform = _choose_platform("Remove which profile?", profiles, allow_all=False)
            if platform:
                _print(_run_cmd(runner, app, ["profile", "remove", platform]))
            _pause()
            continue
        _print("Invalid choice.")


def _tokens_menu(runner: CliRunner, app: Any) -> None:
    profiles = _get_profiles(runner, app)
    if not profiles:
        _print("No profiles. Add one under Profiles first.")
        _pause()
        return
    _print("\n--- Tokens ---")
    _print("  1. Set token (store in keychain)")
    _print("  2. Check token")
    _print("  3. Token info (metadata only)")
    _print("  4. Delete token")
    _print("  0. Back")
    c = _input("Choice [0-4]: ").strip()
    if c == "0":
        return
    platform = _choose_platform("Platform?", profiles, allow_all=False)
    if not platform:
        return
    if c == "1":
        _print("You will be prompted for the token (input is hidden).")
        _print(_run_cmd(runner, app, ["token", "set", platform]))
    elif c == "2":
        _print(_run_cmd(runner, app, ["token", "check", platform]))
    elif c == "3":
        _print(_run_cmd(runner, app, ["token", "info", platform]))
    elif c == "4":
        _print(_run_cmd(runner, app, ["token", "delete", platform]))
    else:
        _print("Invalid choice.")
    _pause()


def run_tui(app: Any) -> None:
    """Run the interactive TUI. Uses CliRunner to invoke the same CLI commands."""
    runner = CliRunner()
    if not _ensure_config(runner, app):
        _print("Could not initialize config. Exiting.")
        sys.exit(1)
    while True:
        choice = _main_menu()
        if not choice or choice == "0":
            _print("Bye.")
            break
        if choice == "1":
            _print(_run_cmd(runner, app, ["dashboard"]))
            _pause()
            continue
        if choice == "2":
            _print(_run_cmd(runner, app, ["status"]))
            _pause()
            continue
        if choice == "3":
            _profiles_menu(runner, app)
            continue
        if choice == "4":
            _tokens_menu(runner, app)
            continue
        if choice == "5":
            profiles = _get_profiles(runner, app)
            platform = _choose_platform("Fetch for which platform?", profiles, allow_all=True)
            if platform:
                _print(_run_cmd(runner, app, ["changes", "fetch", platform]))
            _pause()
            continue
        if choice == "6":
            profiles = _get_profiles(runner, app)
            platform = _choose_platform("Report for which platform?", profiles, allow_all=True)
            if platform:
                _print(_run_cmd(runner, app, ["report", platform]))
            _pause()
            continue
        if choice == "7":
            profiles = _get_profiles(runner, app)
            platform = _choose_platform("Calendar for which platform?", profiles, allow_all=True)
            if platform:
                out = _input("Output file [token-doctor.ics]: ").strip() or "token-doctor.ics"
                _print(_run_cmd(runner, app, ["calendar", "export", platform, "-o", out]))
            _pause()
            continue
        if choice == "8":
            days = _input("Within how many days? [7]: ").strip() or "7"
            _print(_run_cmd(runner, app, ["expiring", "--days", days]))
            _pause()
            continue
        if choice == "9":
            profiles = _get_profiles(runner, app)
            platform = _choose_platform("Doctor run for which platform?", profiles, allow_all=True)
            if platform:
                _print(_run_cmd(runner, app, ["doctor", "run", platform]))
            _pause()
            continue
        if choice == "10":
            profiles = _get_profiles(runner, app)
            platform = _choose_platform("Safe-share for which platform?", profiles, allow_all=False)
            if platform:
                _print(_run_cmd(runner, app, ["safe-share", platform]))
            _pause()
            continue
        _print("Invalid choice.")
