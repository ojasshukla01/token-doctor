"""
Dynamic plugin loading via entrypoints and built-in platform packages.

Plugins are discovered from:
1. Entry point group token_doctor.plugins (pyproject.toml).
2. Built-in packages under token_doctor.platforms.* that expose a `plugin` object.
"""

from __future__ import annotations

import importlib
import pkgutil
from typing import TYPE_CHECKING, Any, Protocol

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


def _discover_platform_modules() -> list[tuple[str, Any]]:
    """Discover top-level platform packages (e.g. github, slack) that have a 'plugin' attribute."""
    result: list[tuple[str, Any]] = []
    try:
        import token_doctor.platforms as platforms_pkg
        for _importer, modname, ispkg in pkgutil.walk_packages(
            path=platforms_pkg.__path__,
            prefix=platforms_pkg.__name__ + ".",
        ):
            if modname == "token_doctor.platforms.base":
                continue
            # Only top-level packages: token_doctor.platforms.<name>, not .<name>.plugin
            parts = modname.split(".")
            if len(parts) != 3 or not ispkg:
                continue
            try:
                mod = importlib.import_module(modname)
                plug = getattr(mod, "plugin", None)
                if plug is not None:
                    result.append((parts[-1], plug))
            except Exception:
                continue
    except Exception:
        pass
    return result


def load_plugins_builtin() -> dict[str, Any]:
    """Load built-in platform plugins by discovering token_doctor.platforms subpackages."""
    plugins: dict[str, Any] = {}
    for key, plug in _discover_platform_modules():
        meta = get_plugin_metadata(plug)
        name = meta.get("platform", key)
        plugins[name] = plug
    return plugins


def get_all_plugins() -> dict[str, Any]:
    """Merge entrypoint and built-in plugins (built-in overrides same name)."""
    all_plugs: dict[str, Any] = {}
    all_plugs.update(load_plugins_via_entrypoints())
    all_plugs.update(load_plugins_builtin())
    return all_plugs
