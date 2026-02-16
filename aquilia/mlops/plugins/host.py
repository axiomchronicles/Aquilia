"""
Plugin host — discovers, loads, and manages lifecycle of MLOps plugins.

Plugins are Python packages that expose an ``aquilia_mlops_plugin`` entry
point or implement the ``PluginHook`` protocol from ``_types.py``.
"""

from __future__ import annotations

import importlib
import importlib.metadata
import inspect
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol, Type

logger = logging.getLogger("aquilia.mlops.plugins")

ENTRYPOINT_GROUP = "aquilia_mlops_plugin"


# ── Plugin descriptor ───────────────────────────────────────────────────

class PluginState(str, Enum):
    DISCOVERED = "discovered"
    LOADED = "loaded"
    ACTIVATED = "activated"
    DEACTIVATED = "deactivated"
    ERROR = "error"


@dataclass
class PluginDescriptor:
    name: str
    version: str
    module: str
    state: PluginState = PluginState.DISCOVERED
    instance: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# ── Hook protocol (mirrors _types.PluginHook) ───────────────────────────

class PluginHookProtocol(Protocol):
    """Minimal interface a plugin must satisfy."""

    name: str
    version: str

    def activate(self, ctx: Dict[str, Any]) -> None: ...
    def deactivate(self) -> None: ...


# ── Plugin host ──────────────────────────────────────────────────────────

class PluginHost:
    """
    Central plugin manager.

    **Discovery methods** (in order):

    1. ``discover_entrypoints()`` — scans ``importlib.metadata`` for
       packages declaring the ``aquilia_mlops_plugin`` entry-point group.
    2. ``register(cls_or_instance)`` — manually register a plugin class
       or instance.

    **Lifecycle**:  discover → load → activate → deactivate
    """

    def __init__(self) -> None:
        self._plugins: Dict[str, PluginDescriptor] = {}
        self._hooks: Dict[str, List[Callable]] = {}

    # ── discovery ────────────────────────────────────────────────────────

    def discover_entrypoints(self) -> List[PluginDescriptor]:
        """Scan installed packages for plugins."""
        found: List[PluginDescriptor] = []
        try:
            eps = importlib.metadata.entry_points()
            group = (
                eps.get(ENTRYPOINT_GROUP, [])
                if isinstance(eps, dict)
                else [ep for ep in eps if ep.group == ENTRYPOINT_GROUP]
            )
        except Exception as exc:
            logger.warning("Failed to read entry points: %s", exc)
            return found

        for ep in group:
            desc = PluginDescriptor(
                name=ep.name,
                version="0.0.0",
                module=ep.value if isinstance(ep.value, str) else str(ep),
            )
            self._plugins[ep.name] = desc
            found.append(desc)
            logger.info("Discovered plugin '%s' via entry point", ep.name)

        return found

    def register(self, plugin: Any) -> PluginDescriptor:
        """Manually register a plugin class or instance."""
        if inspect.isclass(plugin):
            instance = plugin()
        else:
            instance = plugin

        name = getattr(instance, "name", type(instance).__name__)
        version = getattr(instance, "version", "0.0.0")

        desc = PluginDescriptor(
            name=name,
            version=version,
            module=type(instance).__module__,
            state=PluginState.LOADED,
            instance=instance,
        )
        self._plugins[name] = desc
        logger.info("Registered plugin '%s' v%s", name, version)
        return desc

    # ── lifecycle ────────────────────────────────────────────────────────

    def load(self, name: str) -> PluginDescriptor:
        """Import and instantiate a discovered plugin."""
        desc = self._plugins.get(name)
        if desc is None:
            raise KeyError(f"Plugin '{name}' not found")

        if desc.state not in (PluginState.DISCOVERED, PluginState.DEACTIVATED):
            return desc

        try:
            module_path, _, attr = desc.module.rpartition(":")
            if not module_path:
                module_path = desc.module
                attr = ""
            mod = importlib.import_module(module_path)
            cls = getattr(mod, attr) if attr else mod
            desc.instance = cls() if inspect.isclass(cls) else cls
            desc.state = PluginState.LOADED
            desc.version = getattr(desc.instance, "version", desc.version)
            logger.info("Loaded plugin '%s'", name)
        except Exception as exc:
            desc.state = PluginState.ERROR
            desc.error = str(exc)
            logger.error("Failed to load plugin '%s': %s", name, exc)

        return desc

    def activate(self, name: str, ctx: Optional[Dict[str, Any]] = None) -> None:
        """Activate a loaded plugin."""
        desc = self._plugins.get(name)
        if desc is None:
            raise KeyError(f"Plugin '{name}' not found")

        if desc.state == PluginState.ACTIVATED:
            return

        if desc.state != PluginState.LOADED:
            self.load(name)
            desc = self._plugins[name]

        try:
            if hasattr(desc.instance, "activate"):
                desc.instance.activate(ctx or {})
            desc.state = PluginState.ACTIVATED
            logger.info("Activated plugin '%s'", name)
        except Exception as exc:
            desc.state = PluginState.ERROR
            desc.error = str(exc)
            logger.error("Failed to activate plugin '%s': %s", name, exc)

    def deactivate(self, name: str) -> None:
        """Deactivate a running plugin."""
        desc = self._plugins.get(name)
        if desc is None:
            return

        if desc.state != PluginState.ACTIVATED:
            return

        try:
            if hasattr(desc.instance, "deactivate"):
                desc.instance.deactivate()
            desc.state = PluginState.DEACTIVATED
            logger.info("Deactivated plugin '%s'", name)
        except Exception as exc:
            desc.state = PluginState.ERROR
            desc.error = str(exc)
            logger.error("Failed to deactivate plugin '%s': %s", name, exc)

    def activate_all(self, ctx: Optional[Dict[str, Any]] = None) -> None:
        for name in list(self._plugins):
            self.activate(name, ctx)

    def deactivate_all(self) -> None:
        for name in list(self._plugins):
            self.deactivate(name)

    # ── hook registration ────────────────────────────────────────────────

    def on(self, event: str, callback: Callable) -> None:
        """Register a hook callback for *event*."""
        self._hooks.setdefault(event, []).append(callback)

    def emit(self, event: str, **kwargs: Any) -> List[Any]:
        """Fire all callbacks for *event* and collect results."""
        results: List[Any] = []
        for cb in self._hooks.get(event, []):
            try:
                results.append(cb(**kwargs))
            except Exception as exc:
                logger.error("Hook '%s' failed: %s", event, exc)
        return results

    # ── queries ──────────────────────────────────────────────────────────

    def list_plugins(self) -> List[PluginDescriptor]:
        return list(self._plugins.values())

    def get(self, name: str) -> Optional[PluginDescriptor]:
        return self._plugins.get(name)

    @property
    def active_plugins(self) -> List[PluginDescriptor]:
        return [p for p in self._plugins.values() if p.state == PluginState.ACTIVATED]
