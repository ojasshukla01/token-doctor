"""
Textual TUI dashboard for token-doctor (2025–2026 stack).

Requires: pip install -e ".[textual]"
Run: token-doctor tui

Same options as token-doctor ui: Dashboard, Status, Profiles, Tokens, Fetch, Report,
Calendar, Expiring, Doctor run, Safe-share. Press m from Dashboard for main menu.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Textual imports only here so the rest of the project does not require textual
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, ScrollableContainer
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, OptionList, Static
from textual.widgets.option_list import Option

# Shared look & feel: dark theme with clear sections and accent
APP_CSS = """
/* App and screens */
TokenDoctorTUI, Screen {
    background: $surface-darken-3;
}

/* Header: always visible - app/screen title */
Header {
    background: $surface-lighten-1;
    color: $text;
    border-bottom: solid $accent;
    padding: 0 2;
    min-height: 3;
    text-style: bold;
}

/* Footer: always visible - key bindings (e.g. e Export, m Menu, r Refresh, q Quit) */
Footer {
    background: $surface-lighten-1;
    color: $text;
    border-top: solid $accent;
    padding: 0 2;
    min-height: 3;
}

/* Section containers: card-like */
.section {
    background: $surface-darken-2;
    border: solid $surface-lighten-1;
    border-title-color: $accent;
    padding: 1 2;
    margin: 0 1 1 1;
    height: auto;
}

.section-title {
    color: $accent;
    text-style: bold;
    padding-bottom: 1;
}

/* Option lists: focused and tidy */
OptionList {
    background: $surface-darken-2;
    border: solid $surface-lighten-1;
    padding: 1 2;
    margin: 1 2;
    min-height: 10;
}

OptionList:focus {
    border: solid $accent;
}

OptionList .option-list--option-highlighted {
    background: $surface-lighten-1;
}

/* Data table */
DataTable {
    background: $surface-darken-2;
    border: solid $surface-lighten-1;
    padding: 0 1;
    margin: 0 1 1 1;
}

DataTable .datatable--header {
    background: $surface-lighten-1;
    color: $text;
    text-style: bold;
}

DataTable .datatable--cursor {
    background: $surface-lighten-1;
}

/* Output / static content */
#cli-output, .muted {
    color: $text-muted;
    padding: 1 2;
}

#alerts {
    color: $warning;
}

/* Scrollable area */
ScrollableContainer {
    padding: 0 1;
}
"""


def _load_config() -> Any:
    from token_doctor.core.cache import init_db
    from token_doctor.core.config import ensure_config_dir, load_config

    try:
        config = load_config()
    except Exception:
        config_dir = Path.home() / ".config" / "token-doctor"
        from token_doctor.core.config import TokenDoctorConfig
        config = TokenDoctorConfig(config_dir=config_dir)
    ensure_config_dir(config)
    init_db(config.effective_db_path)
    return config


def _get_status_rows(config: Any) -> list[tuple[str, str, str]]:
    """Return [(platform, token_status, events_str), ...] for enabled profiles."""
    from token_doctor.core.cache import get_event_counts
    from token_doctor.core.secrets import get_token

    counts = get_event_counts(config.effective_db_path)
    rows: list[tuple[str, str, str]] = []
    for p in config.profiles:
        if not p.enabled:
            continue
        tok = get_token(p.platform, config.config_dir)
        status_str = "set" if tok else "not set"
        n = counts.get(p.platform, 0)
        rows.append((p.platform, status_str, str(n)))
    return rows


def _get_deadlines(config: Any, limit: int = 5) -> list[str]:
    from token_doctor.core.cache import get_next_deadlines

    deadlines = get_next_deadlines(config.effective_db_path, limit=limit)
    lines: list[str] = []
    for e in deadlines:
        ed = e.effective_date.date().isoformat() if e.effective_date else "?"
        lines.append(f"  {ed} [{e.platform}] {e.title[:50]}")
    return lines


def _get_recent_events(config: Any, limit: int = 5) -> list[str]:
    """Recent events (sorted by date, newest first), up to limit."""
    return _get_all_events_formatted(config, limit=limit)


def _event_type_tag(e: Any) -> str:
    """Short tag for version/sunset-related event types; empty for others."""
    from token_doctor.core.schema import EventType

    et = getattr(e, "event_type", None)
    if et is None:
        return ""
    if et == EventType.SUNSET or et == EventType.DEPRECATION:
        ed = getattr(e, "effective_date", None)
        if ed:
            return f" [{et.value} {ed.date().isoformat()}]"
        return f" [{et.value}]"
    if et in (EventType.VERSION_UPGRADE, EventType.BREAKING_CHANGE):
        return f" [{et.value}]"
    return ""


def _get_all_events_formatted(config: Any, limit: int | None = None) -> list[str]:
    """All cached events formatted (newest first). If limit is None, return all.
    Sunset/deprecation events show type and effective date; version_upgrade and breaking_change show type."""
    from token_doctor.core.cache import get_events

    all_events: list[tuple[str, Any]] = []
    min_dt = datetime(1970, 1, 1, tzinfo=timezone.utc)
    for p in config.profiles:
        if not p.enabled:
            continue
        events = get_events(config.effective_db_path, platform=p.platform)
        for e in events:
            all_events.append((e.platform, e))
    all_events.sort(key=lambda x: (x[1].published_at or x[1].effective_date or min_dt), reverse=True)
    if limit is not None:
        all_events = all_events[:limit]
    lines: list[str] = []
    for platform, e in all_events:
        pub = e.published_at or e.effective_date
        pub_str = pub.isoformat()[:10] if pub else ""
        tag = _event_type_tag(e)
        # Keep line readable: tag then title (truncate title if needed)
        max_title = 60 - len(tag) if tag else 60
        if max_title < 20:
            max_title = 50
        lines.append(f"  [{platform}] {pub_str}{tag} {e.title[:max_title]}")
    return lines


def _run_cli(args: list[str]) -> str:
    """Run CLI with args; return combined stdout/stderr."""
    from typer.testing import CliRunner

    from token_doctor.cli.main import app as cli_app

    result = CliRunner().invoke(cli_app, args)
    # CliRunner mixes stdout/stderr in .output unless mix_stderr=False
    out = getattr(result, "output", None) or result.stdout or ""
    try:
        if getattr(result, "stderr", None) and result.stderr.strip():
            out = (out + "\n" + result.stderr).strip()
    except ValueError:
        pass  # stderr not separately captured
    return out.strip() if out else f"(exit code {result.exit_code})"


def _get_profiles() -> list[str]:
    """Return enabled profile platform names."""
    try:
        config = _load_config()
        return [p.platform for p in config.profiles if p.enabled]
    except Exception:
        return []


def _get_available_platforms() -> list[str]:
    """Return sorted list of available platform names."""
    from token_doctor.core.plugin_loader import list_platform_names
    return list(list_platform_names())


def _get_alerts_text(config: Any) -> str:
    """Return alert lines for token expiry and sunset (30/15/7/1 day thresholds)."""
    from token_doctor.core.alerts import get_sunset_alerts, get_token_expiry_alerts

    lines: list[str] = []
    for token_alert in get_token_expiry_alerts(config, within_days=30):
        lines.append(f"  [Token] {token_alert.platform}: expires in {token_alert.days_until} days")
    for sunset_alert in get_sunset_alerts(config, config.effective_db_path, within_days=30):
        lines.append(f"  [Sunset] {sunset_alert.platform}: in {sunset_alert.days_until} days — {sunset_alert.title[:45]}")
    if not lines:
        return ""
    return "\n".join(lines)


def _push_platform_picker_or_message(
    app: App[Any],
    title: str,
    allow_all: bool,
    cmd_template: list[str],
    output_title: str,
) -> None:
    """Push PlatformPickerScreen if profiles exist, else OutputScreen with message."""
    if not _get_profiles():
        app.push_screen(OutputScreen("No profiles. Add one via: token-doctor profile add <platform>", title=output_title))
        return
    app.push_screen(PlatformPickerScreen(
        title=title,
        allow_all=allow_all,
        cmd_template=cmd_template,
        output_title=output_title,
    ))


class OutputScreen(Screen[Any]):
    """Show CLI command output with Back to return."""

    TITLE = "token-doctor"
    BINDINGS = [
        Binding("b", "back", "Back"),
        Binding("q", "quit", "Quit"),
    ]

    DEFAULT_CSS = """
    OutputScreen { background: $surface-darken-3; }
    #cli-output {
        padding: 2 2;
        color: $text;
        border: solid $surface-lighten-1;
        margin: 1 2;
        background: $surface-darken-2;
    }
    """

    def __init__(self, output: str = "", title: str = "Output") -> None:
        self._output = output
        self._title = title
        self._sub_title_storage = ""  # base Screen sets sub_title in __init__; we need a setter
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield ScrollableContainer(Static(self._output or "(no output)", id="cli-output"))
        yield Footer()

    def on_mount(self) -> None:
        self.app.title = "token-doctor"
        self.app.sub_title = self._title

    @property
    def sub_title(self) -> str:
        return self._title

    @sub_title.setter
    def sub_title(self, value: str) -> None:
        self._sub_title_storage = value

    def action_back(self) -> None:
        self.app.pop_screen()


class AllEventsScreen(Screen[Any]):
    """Show all cached events (scrollable), newest first."""

    TITLE = "token-doctor"
    SUB_TITLE = "All events"
    BINDINGS = [
        Binding("b", "back", "Back"),
        Binding("q", "quit", "Quit"),
    ]

    DEFAULT_CSS = """
    AllEventsScreen { background: $surface-darken-3; }
    #all-events {
        padding: 1 2;
        color: $text;
        border: solid $surface-lighten-1;
        margin: 1 2;
        background: $surface-darken-2;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield ScrollableContainer(Static("Loading…", id="all-events"))
        yield Footer()

    def on_mount(self) -> None:
        self.app.title = "token-doctor"
        self.app.sub_title = "All events"
        try:
            config = _load_config()
            lines = _get_all_events_formatted(config, limit=None)
            if lines:
                header = "  Sunset/deprecation show deadline; version_upgrade and breaking_change tagged.\n"
                text = header + "\n".join(lines)
            else:
                text = "  No events in cache. Run Fetch for your platform(s) to load events."
        except Exception as e:
            text = f"[red]Error: {e}[/red]"
        self.query_one("#all-events", Static).update(text)

    def action_back(self) -> None:
        self.app.pop_screen()


class PlatformPickerScreen(Screen[Any]):
    """Pick a platform (or All) then run a CLI command."""

    TITLE = "token-doctor"
    BINDINGS = [Binding("b", "back", "Back"), Binding("q", "quit", "Quit")]

    DEFAULT_CSS = """
    PlatformPickerScreen { background: $surface-darken-3; }
    #platform-list {
        padding: 1 2;
        margin: 1 2;
        min-width: 32;
        border: solid $surface-lighten-1;
        background: $surface-darken-2;
    }
    """

    def __init__(
        self,
        title: str = "Choose platform",
        allow_all: bool = True,
        cmd_template: list[str] | None = None,
        output_title: str = "Output",
    ) -> None:
        self._title = title
        self._allow_all = allow_all
        self._cmd_template = cmd_template or ["report", "{platform}"]
        self._output_title = output_title
        self._sub_title_storage = ""
        super().__init__()

    @property
    def sub_title(self) -> str:
        return self._title

    @sub_title.setter
    def sub_title(self, value: str) -> None:
        self._sub_title_storage = value

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        profiles = _get_profiles()
        options: list[Option | None] = []
        if self._allow_all and profiles:
            options.append(Option("All (all platforms)", id="all"))
        for p in profiles:
            options.append(Option(p, id=p))
        if not options:
            options.append(Option("(No profiles — add one first)", id="", disabled=True))
        yield OptionList(*options, id="platform-list")
        yield Footer()

    def on_mount(self) -> None:
        self.app.title = "token-doctor"
        self.app.sub_title = self._title

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        platform = (event.option.id or "").strip()
        if not platform:
            return
        if platform == "all":
            platform = "all"
        profiles = _get_profiles()
        if not profiles:
            return
        if platform != "all" and platform not in profiles:
            return
        args = [s if s != "{platform}" else platform for s in self._cmd_template]
        output = _run_cli(args)
        self.app.pop_screen()
        self.app.push_screen(OutputScreen(output, title=self._output_title))

    def action_back(self) -> None:
        self.app.pop_screen()


class ProfilesSubmenuScreen(Screen[Any]):
    """Profiles: List / Add / Remove."""

    TITLE = "token-doctor"
    SUB_TITLE = "Profiles"
    BINDINGS = [Binding("b", "back", "Back"), Binding("q", "quit", "Quit")]

    DEFAULT_CSS = """
    ProfilesSubmenuScreen { background: $surface-darken-3; }
    #profiles-list { padding: 1 2; margin: 1 2; border: solid $surface-lighten-1; background: $surface-darken-2; }
    """

    def on_mount(self) -> None:
        self.app.title = "token-doctor"
        self.app.sub_title = "Profiles"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield OptionList(
            Option("List profiles", id="list"),
            Option("Add profile", id="add"),
            Option("Remove profile", id="remove"),
            id="profiles-list",
        )
        yield Footer()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        opt = event.option.id or ""
        if opt == "list":
            output = _run_cli(["profile", "list"])
            self.app.pop_screen()
            self.app.push_screen(OutputScreen(output, title="Profiles"))
        elif opt == "add":
            platforms = _get_available_platforms()
            msg = "To add a profile, run in terminal:\n  token-doctor profile add <platform>\n\nAvailable (first 30): " + ", ".join(platforms[:30])
            if len(platforms) > 30:
                msg += "\n  ... and more."
            self.app.pop_screen()
            self.app.push_screen(OutputScreen(msg, title="Add profile"))
        elif opt == "remove":
            profiles = _get_profiles()
            if not profiles:
                self.app.pop_screen()
                self.app.push_screen(OutputScreen("No profiles. Add one first.", title="Remove profile"))
                return
            self.app.pop_screen()
            self.app.push_screen(PlatformPickerScreen(
                title="Remove which profile?",
                allow_all=False,
                cmd_template=["profile", "remove", "{platform}"],
                output_title="Remove profile",
            ))

    def action_back(self) -> None:
        self.app.pop_screen()


class TokensSubmenuScreen(Screen[Any]):
    """Tokens: Set / Check / Info / Delete (then pick platform)."""

    TITLE = "token-doctor"
    SUB_TITLE = "Tokens"
    BINDINGS = [Binding("b", "back", "Back"), Binding("q", "quit", "Quit")]

    DEFAULT_CSS = """
    TokensSubmenuScreen { background: $surface-darken-3; }
    #tokens-list { padding: 1 2; margin: 1 2; border: solid $surface-lighten-1; background: $surface-darken-2; }
    """

    def on_mount(self) -> None:
        self.app.title = "token-doctor"
        self.app.sub_title = "Tokens"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield OptionList(
            Option("Set token (store in keychain)", id="set"),
            Option("Check token", id="check"),
            Option("Token info (metadata only)", id="info"),
            Option("Delete token", id="delete"),
            id="tokens-list",
        )
        yield Footer()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        opt = event.option.id or ""
        profiles = _get_profiles()
        if not profiles:
            self.app.pop_screen()
            self.app.push_screen(OutputScreen("No profiles. Add one under Profiles first.", title="Tokens"))
            return
        if opt == "set":
            msg = "To set a token (you will be prompted securely), run in terminal:\n  token-doctor token set <platform>\n\nYour profiles: " + ", ".join(profiles)
            self.app.pop_screen()
            self.app.push_screen(OutputScreen(msg, title="Set token"))
            return
        cmd_map = {"check": ["token", "check", "{platform}"], "info": ["token", "info", "{platform}"], "delete": ["token", "delete", "{platform}"]}
        if opt not in cmd_map:
            return
        self.app.pop_screen()
        self.app.push_screen(PlatformPickerScreen(
            title="Which platform?",
            allow_all=False,
            cmd_template=cmd_map[opt],
            output_title=f"Token {opt}",
        ))

    def action_back(self) -> None:
        self.app.pop_screen()


class ExpiringSubmenuScreen(Screen[Any]):
    """Expiring tokens: choose within how many days to check."""

    TITLE = "token-doctor"
    SUB_TITLE = "Expiring tokens"
    BINDINGS = [Binding("b", "back", "Back"), Binding("q", "quit", "Quit")]

    DEFAULT_CSS = """
    ExpiringSubmenuScreen { background: $surface-darken-3; }
    #expiring-list { padding: 1 2; margin: 1 2; border: solid $surface-lighten-1; background: $surface-darken-2; }
    """

    def on_mount(self) -> None:
        self.app.title = "token-doctor"
        self.app.sub_title = "Expiring tokens"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield OptionList(
            Option("Within 7 days", id="7"),
            Option("Within 15 days", id="15"),
            Option("Within 30 days", id="30"),
            id="expiring-list",
        )
        yield Footer()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        days = event.option.id or "7"
        if days not in ("7", "15", "30"):
            return
        output = _run_cli(["expiring", "--days", days])
        if not output.strip():
            output = f"No tokens with JWT expiry in the next {days} days.\n\n(Only tokens that include an expiry in the JWT are checked.)"
        self.app.pop_screen()
        self.app.push_screen(OutputScreen(output, title=f"Expiring (within {days} days)"))

    def action_back(self) -> None:
        self.app.pop_screen()


class MenuScreen(Screen[Any]):
    """Main menu: dashboard, status, profiles, tokens, fetch, report, calendar, expiring, doctor, safe-share."""

    TITLE = "token-doctor"
    SUB_TITLE = "Main menu"
    BINDINGS = [
        Binding("q", "quit", "Quit"),
    ]

    DEFAULT_CSS = """
    MenuScreen { background: $surface-darken-3; }
    #menu-list {
        padding: 1 2;
        margin: 1 2 2 2;
        min-width: 44;
        max-width: 60;
        border: solid $accent;
        background: $surface-darken-2;
    }
    #menu-welcome {
        padding: 1 2 0 2;
        color: $text;
    }
    """

    def on_mount(self) -> None:
        self.app.title = "token-doctor"
        self.app.sub_title = "Main menu"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Static("Choose an option (↑↓ to move, Enter to select)", id="menu-welcome")
        yield OptionList(
            Option("1. Dashboard (status + recent events)", id="1"),
            Option("2. Status (token + event summary)", id="2"),
            Option("3. Profiles (list / add / remove)", id="3"),
            Option("4. Tokens (set / check / info / delete)", id="4"),
            Option("5. Fetch changes (changelog feeds)", id="5"),
            Option("6. Report (Markdown / JSON / HTML)", id="6"),
            Option("7. Calendar export (ICS)", id="7"),
            Option("8. Expiring tokens", id="8"),
            Option("9. Doctor run (check + fetch + report)", id="9"),
            Option("10. Safe-share (export diagnostics)", id="10"),
            Option("11. All events", id="11"),
            Option("0. Exit", id="0"),
            id="menu-list",
        )
        yield Footer()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        opt_id = event.option.id if event.option.id else ""
        if opt_id == "0":
            self.app.exit(0)
            return
        if opt_id == "1":
            self.app.pop_screen()
            self.app.push_screen(DashboardScreen())
            return
        if opt_id == "2":
            output = _run_cli(["status"])
            self.app.push_screen(OutputScreen(output, title="Status"))
            return
        if opt_id == "3":
            self.app.push_screen(ProfilesSubmenuScreen())
            return
        if opt_id == "4":
            self.app.push_screen(TokensSubmenuScreen())
            return
        if opt_id == "5":
            _push_platform_picker_or_message(
                self.app,
                title="Fetch for which platform?",
                allow_all=True,
                cmd_template=["changes", "fetch", "{platform}"],
                output_title="Fetch changes",
            )
            return
        if opt_id == "6":
            _push_platform_picker_or_message(
                self.app,
                title="Report for which platform?",
                allow_all=True,
                cmd_template=["report", "{platform}"],
                output_title="Report",
            )
            return
        if opt_id == "7":
            _push_platform_picker_or_message(
                self.app,
                title="Calendar for which platform?",
                allow_all=True,
                cmd_template=["calendar", "export", "{platform}", "-o", "token-doctor.ics"],
                output_title="Calendar",
            )
            return
        if opt_id == "8":
            self.app.push_screen(ExpiringSubmenuScreen())
            return
        if opt_id == "9":
            _push_platform_picker_or_message(
                self.app,
                title="Doctor run for which platform?",
                allow_all=True,
                cmd_template=["doctor", "run", "{platform}"],
                output_title="Doctor run",
            )
            return
        if opt_id == "10":
            _push_platform_picker_or_message(
                self.app,
                title="Safe-share for which platform?",
                allow_all=False,
                cmd_template=["safe-share", "{platform}"],
                output_title="Safe-share",
            )
            return
        if opt_id == "11":
            self.app.push_screen(AllEventsScreen())
            return


class DashboardScreen(Screen[Any]):
    """Main dashboard: status table, alerts, deadlines, recent events."""

    TITLE = "token-doctor"
    SUB_TITLE = "Dashboard"
    BINDINGS = [
        Binding("e", "export_calendar", "Export calendar"),
        Binding("v", "view_all_events", "All events"),
        Binding("m", "menu", "Menu"),
        Binding("r", "refresh", "Refresh"),
        Binding("q", "quit", "Quit"),
    ]

    DEFAULT_CSS = """
    DashboardScreen { background: $surface-darken-3; }
    .dashboard-section {
        background: $surface-darken-2;
        border: solid $surface-lighten-1;
        padding: 1 2;
        margin: 0 1 1 1;
        height: auto;
    }
    .dashboard-section-title {
        color: $accent;
        text-style: bold;
        padding-bottom: 1;
    }
    #status-table {
        margin-bottom: 1;
    }
    #deadlines, #events, #status-empty {
        color: $text-muted;
    }
    #alerts {
        color: $warning;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield ScrollableContainer(
            Container(
                Static("Status", classes="dashboard-section-title"),
                DataTable(id="status-table", cursor_type="none"),
                Static("", id="status-empty"),
                classes="dashboard-section",
            ),
            Container(
                Static("Alerts (30 / 15 / 7 / 1 day)", classes="dashboard-section-title"),
                Static("", id="alerts"),
                classes="dashboard-section",
            ),
            Container(
                Static("Next deadlines", classes="dashboard-section-title"),
                Static("", id="deadlines"),
                classes="dashboard-section",
            ),
            Container(
                Static("Recent events (sunset/deprecation show deadline)", classes="dashboard-section-title"),
                Static("", id="events"),
                classes="dashboard-section",
            ),
        )
        yield Footer()

    def on_mount(self) -> None:
        self.app.title = "token-doctor"
        self.app.sub_title = "Dashboard"
        self._refresh_data()

    def action_refresh(self) -> None:
        self._refresh_data()

    def _refresh_data(self) -> None:
        try:
            config = _load_config()
        except Exception as e:
            self._show_error(str(e))
            return
        # Status table
        table = self.query_one("#status-table", DataTable)
        table.clear(columns=True)
        rows = _get_status_rows(config)
        if rows:
            table.add_columns("Platform", "Token", "Events")
            for r in rows:
                table.add_row(r[0], r[1], r[2])
            self.query_one("#status-empty", Static).update("")
        else:
            self.query_one("#status-empty", Static).update("No profiles. Run: token-doctor profile add <platform>")
        # Alerts (30/15/7/1 day token expiry and sunset)
        alerts_text = _get_alerts_text(config)
        self.query_one("#alerts", Static).update(alerts_text if alerts_text else "  None")
        # Deadlines
        deadline_lines = _get_deadlines(config)
        self.query_one("#deadlines", Static).update("\n".join(deadline_lines) if deadline_lines else "  None")
        # Recent events (show more on dashboard)
        event_lines = _get_recent_events(config, limit=20)
        self.query_one("#events", Static).update("\n".join(event_lines) if event_lines else "  None")

    def _show_error(self, msg: str) -> None:
        self.query_one("#status-empty", Static).update(f"[red]Error: {msg}[/red]")
        self.query_one("#alerts", Static).update("")
        self.query_one("#deadlines", Static).update("")
        self.query_one("#events", Static).update("")

    def action_export_calendar(self) -> None:
        """Export calendar (ICS) for reminders; show output."""
        try:
            config = _load_config()
        except Exception:
            return
        out_path = config.config_dir / "token-doctor.ics"
        output = _run_cli(["calendar", "export", "all", "-o", str(out_path)])
        self.app.push_screen(OutputScreen(output or f"Wrote {out_path}", title="Export calendar"))

    def action_view_all_events(self) -> None:
        """Open scrollable screen with all cached events."""
        self.app.push_screen(AllEventsScreen())

    def action_menu(self) -> None:
        self.app.push_screen(MenuScreen())


class TokenDoctorTUI(App[Any]):
    """Token-doctor Textual TUI (dashboard)."""

    TITLE = "token-doctor"
    SUB_TITLE = "Dashboard"
    BINDINGS = [
        Binding("q", "quit", "Quit"),
    ]

    DEFAULT_CSS = APP_CSS

    def compose(self) -> ComposeResult:
        # Content comes from the pushed DashboardScreen
        yield from ()

    def on_mount(self) -> None:
        # Start with main menu (same options as token-doctor ui)
        self.push_screen(MenuScreen())


def run_textual_app() -> None:
    """Run the Textual app (entry point from CLI)."""
    app = TokenDoctorTUI()
    app.run()


def textual_available() -> bool:
    """Return True if textual is installed (for CLI to show helpful message)."""
    try:
        import textual  # noqa: F401
        return True
    except ImportError:
        return False
