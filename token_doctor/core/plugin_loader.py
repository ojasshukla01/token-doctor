"""
Dynamic plugin loading via entrypoints and built-in platform packages.

Plugins are discovered from:
1. Entry point group token_doctor.plugins (pyproject.toml).
2. Built-in packages under token_doctor.platforms.* that expose a `plugin` object.
"""

from __future__ import annotations

import importlib
import pkgutil
from typing import TYPE_CHECKING, Any, Iterable, Protocol

if TYPE_CHECKING:
    from token_doctor.core.schema import CheckResult, NormalizedEvent

    class PluginProtocol(Protocol):
        @property
        def metadata(self) -> dict[str, Any]: ...

        def token_checks(self, token: str, config: Any) -> list[CheckResult]: ...

        def collect_changes(self, since: Any) -> list[NormalizedEvent]: ...

        def collect_status(self) -> list[NormalizedEvent] | None: ...
else:
    PluginProtocol = None


def get_plugin_metadata(plugin: Any) -> dict[str, Any]:
    """Extract plugin manifest: platform name, auth types, docs, declared endpoints."""
    return getattr(plugin, "metadata", {})


def load_plugins_via_entrypoints() -> dict[str, Any]:
    """Load plugins from entry point group token_doctor.plugins."""
    plugins: dict[str, Any] = {}
    try:
        from importlib.metadata import entry_points

        eps = entry_points()
        if hasattr(eps, "select"):
            group: Any = eps.select(group="token_doctor.plugins")
        else:
            group = getattr(eps, "get", lambda _k: [])("token_doctor.plugins") or []
        for ep in group:
            try:
                plug = ep.load()
                meta = get_plugin_metadata(plug)
                name = meta.get("platform", ep.name)
                plugins[name] = plug
            except Exception:
                continue
    except Exception:
        pass
    return plugins


def _list_platform_names() -> list[str]:
    """List platform names (package names) without loading modules."""
    names: list[str] = []
    try:
        import token_doctor.platforms as platforms_pkg
        for _importer, modname, ispkg in pkgutil.walk_packages(
            path=platforms_pkg.__path__,
            prefix=platforms_pkg.__name__ + ".",
        ):
            if modname == "token_doctor.platforms.base":
                continue
            parts = modname.split(".")
            if len(parts) == 3 and ispkg:
                names.append(parts[-1])
    except Exception:
        pass
    return names


def _discover_platform_modules(
    only_platforms: list[str] | None = None,
) -> list[tuple[str, Any]]:
    """Discover top-level platform packages that have a 'plugin' attribute. If only_platforms is set, load only those."""
    result: list[tuple[str, Any]] = []
    try:
        import token_doctor.platforms as platforms_pkg
        for _importer, modname, ispkg in pkgutil.walk_packages(
            path=platforms_pkg.__path__,
            prefix=platforms_pkg.__name__ + ".",
        ):
            if modname == "token_doctor.platforms.base":
                continue
            parts = modname.split(".")
            if len(parts) != 3 or not ispkg:
                continue
            name = parts[-1]
            if only_platforms is not None and name not in only_platforms:
                continue
            try:
                mod = importlib.import_module(modname)
                plug = getattr(mod, "plugin", None)
                if plug is not None:
                    result.append((name, plug))
            except Exception:
                continue
    except Exception:
        pass
    return result


def load_plugins_builtin(
    only_platforms: list[str] | None = None,
) -> dict[str, Any]:
    """Load built-in platform plugins. If only_platforms is set, load only those (lazy)."""
    plugins: dict[str, Any] = {}
    for key, plug in _discover_platform_modules(only_platforms=only_platforms):
        meta = get_plugin_metadata(plug)
        name = meta.get("platform", key)
        plugins[name] = plug
    return plugins


def get_all_plugins(only_platforms: list[str] | None = None) -> dict[str, Any]:
    """Merge entrypoint and built-in plugins. If only_platforms is set, only load those built-in (lazy)."""
    all_plugs: dict[str, Any] = {}
    all_plugs.update(load_plugins_via_entrypoints())
    builtin = load_plugins_builtin(only_platforms=only_platforms)
    # If only_platforms: entrypoints might have same name; builtin overrides. Include only requested from entrypoints too.
    if only_platforms is not None:
        for name, _plug in list(all_plugs.items()):
            if name not in only_platforms:
                del all_plugs[name]
    all_plugs.update(builtin)
    return all_plugs


def list_platform_names() -> list[str]:
    """Return sorted list of all known platform names (for fuzzy match)."""
    names = set(_list_platform_names())
    try:
        from importlib.metadata import entry_points
        eps = entry_points()
        group: Iterable[Any]
        if hasattr(eps, "select"):
            group = eps.select(group="token_doctor.plugins")
        else:
            group = getattr(eps, "get", lambda _k: [])("token_doctor.plugins") or []
        for ep in group:
            meta = {}
            try:
                plug = ep.load()
                meta = get_plugin_metadata(plug)
            except Exception:
                pass
            names.add(meta.get("platform", ep.name))
    except Exception:
        pass
    return sorted(names)
