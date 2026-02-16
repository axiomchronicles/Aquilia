"""
Aquilia Testing - Config Override Utilities.

Provides ``override_settings`` context manager / decorator and
``TestConfig`` for replacing server configuration during tests.
"""

from __future__ import annotations

import copy
import functools
from contextlib import contextmanager
from typing import Any, Callable, Dict, Optional

from aquilia.config import ConfigLoader


class TestConfig:
    """
    Lightweight config wrapper for test overrides.

    Wraps an existing :class:`ConfigLoader` and overlays test-specific
    settings without mutating the original.

    Usage::

        cfg = TestConfig(base_loader, debug=True, mode="test")
        assert cfg.get("debug") is True
        assert "debug" in cfg
        assert cfg["debug"] is True
    """

    __slots__ = ("_base", "_overrides", "_merged")

    def __init__(self, base: Optional[ConfigLoader] = None, **overrides: Any):
        self._base = base
        self._overrides = overrides
        self._merged: Optional[dict] = None

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieve a config value using dot-notation.

        Override values take precedence over the base config.
        """
        # Fast path – check overrides first
        parts = key.split(".")
        ref: Any = self._overrides
        for part in parts:
            if isinstance(ref, dict) and part in ref:
                ref = ref[part]
            else:
                ref = _SENTINEL
                break
        if ref is not _SENTINEL:
            return ref

        # Fallback to base
        if self._base is not None:
            return self._base.get(key, default)
        return default

    def set(self, key: str, value: Any) -> None:
        """Set a config value using dot-notation (mutates overrides)."""
        parts = key.split(".")
        ref = self._overrides
        for part in parts[:-1]:
            ref = ref.setdefault(part, {})
        ref[parts[-1]] = value
        self._merged = None  # invalidate cache

    def has(self, key: str) -> bool:
        """Check if a config key exists."""
        return self.get(key, _SENTINEL) is not _SENTINEL

    def keys(self) -> list:
        """Return top-level config keys."""
        return list(self.to_dict().keys())

    @property
    def config_data(self) -> dict:
        """Return merged config dict (compatible with ConfigLoader)."""
        return self.to_dict()

    def to_dict(self) -> dict:
        """Return merged config as a plain dictionary."""
        if self._merged is None:
            base_dict = self._base.config_data if self._base else {}
            self._merged = _deep_merge(copy.deepcopy(base_dict), self._overrides)
        return self._merged

    # -- Dict-like interface ---------------------------------------------

    def __contains__(self, key: str) -> bool:
        return self.has(key)

    def __getitem__(self, key: str) -> Any:
        val = self.get(key, _SENTINEL)
        if val is _SENTINEL:
            raise KeyError(key)
        return val

    def __repr__(self) -> str:
        keys = list(self.to_dict().keys())
        return f"<TestConfig keys={keys}>"

    # Proxy common ConfigLoader accessors --------------------------------

    def get_cache_config(self) -> dict:
        return self.get("integrations.cache", {}) or self.get("cache", {})

    def get_session_config(self) -> dict:
        return self.get("integrations.sessions", {}) or self.get("sessions", {})

    def get_auth_config(self) -> dict:
        return self.get("integrations.auth", {}) or self.get("auth", {})

    def get_mail_config(self) -> dict:
        return self.get("integrations.mail", {}) or self.get("mail", {})

    def get_template_config(self) -> dict:
        return self.get("integrations.templates", {}) or self.get("templates", {})


_SENTINEL = object()


# -----------------------------------------------------------------------
# override_settings – Context manager / decorator
# -----------------------------------------------------------------------

class override_settings:
    """
    Temporarily override Aquilia config values.

    Works as both a **context manager** and a **decorator** – inspired by
    Django's ``override_settings``.

    Context manager::

        with override_settings(DEBUG=True, CACHE_BACKEND="memory"):
            ...

    Decorator::

        @override_settings(DEBUG=True)
        async def test_debug_mode():
            ...

    Implementation notes:
        * Patches the *active* ``ConfigLoader`` instance (if one exists in
          the test server/case) and restores it on exit.
        * Thread-safe within a single asyncio event loop (tests are
          sequential in pytest-asyncio auto mode).
    """

    def __init__(self, **overrides: Any):
        self._overrides = overrides
        self._saved: Dict[str, Any] = {}
        self._target: Optional[ConfigLoader] = None

    # -- Context manager -------------------------------------------------

    def __enter__(self):
        self._apply()
        return self

    def __exit__(self, *exc_info):
        self._restore()

    # -- Async context manager -------------------------------------------

    async def __aenter__(self):
        self._apply()
        return self

    async def __aexit__(self, *exc_info):
        self._restore()

    # -- Decorator -------------------------------------------------------

    def __call__(self, func: Callable):
        import inspect
        if inspect.iscoroutinefunction(func) or _is_async(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                self._apply()
                try:
                    return await func(*args, **kwargs)
                finally:
                    self._restore()

            return async_wrapper
        else:

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                self._apply()
                try:
                    return func(*args, **kwargs)
                finally:
                    self._restore()

            return sync_wrapper

    # -- Internals -------------------------------------------------------

    def _apply(self):
        """Inject overrides into the global config registry."""
        target = _get_active_config()
        if target is None:
            return
        self._target = target
        for key, value in self._overrides.items():
            # Normalise UPPER_SNAKE → dot.notation (e.g. CACHE_BACKEND → cache.backend)
            dot_key = key.lower().replace("__", ".")
            self._saved[dot_key] = target.get(dot_key)
            _set_nested(target.config_data, dot_key, value)

    def _restore(self):
        """Restore original config values."""
        if self._target is None:
            return
        for dot_key, original_value in self._saved.items():
            if original_value is None:
                _delete_nested(self._target.config_data, dot_key)
            else:
                _set_nested(self._target.config_data, dot_key, original_value)
        self._saved.clear()
        self._target = None


# -----------------------------------------------------------------------
# Module-level active config registry
# -----------------------------------------------------------------------

_active_config: Optional[ConfigLoader] = None


def set_active_config(cfg: ConfigLoader) -> None:
    """Register the config loader used by the running test server."""
    global _active_config
    _active_config = cfg


def get_active_config() -> Optional[ConfigLoader]:
    """Return the active config loader."""
    return _active_config


def _get_active_config() -> Optional[ConfigLoader]:
    return _active_config


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

def _deep_merge(base: dict, overrides: dict) -> dict:
    """Recursively merge *overrides* into *base* (mutates base)."""
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def _set_nested(data: dict, dot_key: str, value: Any):
    parts = dot_key.split(".")
    ref = data
    for part in parts[:-1]:
        ref = ref.setdefault(part, {})
    ref[parts[-1]] = value


def _delete_nested(data: dict, dot_key: str):
    parts = dot_key.split(".")
    ref = data
    for part in parts[:-1]:
        ref = ref.get(part, {})
        if not isinstance(ref, dict):
            return
    ref.pop(parts[-1], None)


def _is_async(func: Callable) -> bool:
    import inspect
    return inspect.iscoroutinefunction(func) or inspect.isasyncgenfunction(func)
