"""
Aquilia Testing - TestServer Factory.

Creates a lightweight, fully-wired :class:`AquiliaServer` instance
suitable for unit / integration testing.  All subsystems are booted
in ``TEST`` mode with sensible defaults (memory stores, no external
connections).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional, Sequence, Type

from aquilia.aquilary.core import RegistryMode
from aquilia.config import ConfigLoader
from aquilia.manifest import AppManifest
from aquilia.server import AquiliaServer

from .config import TestConfig, set_active_config

logger = logging.getLogger("aquilia.testing.server")


class TestServer:
    """
    Lightweight test server wrapping :class:`AquiliaServer`.

    Provides helpers for:
    - Quick setup / teardown via ``start()`` / ``stop()`` (or async-with)
    - Accessing the DI container, config, fault engine, etc.
    - Config overrides
    - Manifest injection

    Usage::

        server = TestServer(manifests=[my_manifest])
        await server.start()
        ...
        await server.stop()

    Or as an async context manager::

        async with TestServer(manifests=[my_manifest]) as srv:
            client = TestClient(srv)
            resp = await client.get("/")
    """

    def __init__(
        self,
        manifests: Optional[Sequence[AppManifest]] = None,
        config: Optional[ConfigLoader] = None,
        config_overrides: Optional[Dict[str, Any]] = None,
        mode: RegistryMode = RegistryMode.TEST,
        *,
        debug: bool = True,
        enable_cache: bool = False,
        enable_sessions: bool = False,
        enable_auth: bool = False,
        enable_mail: bool = False,
        enable_templates: bool = False,
    ):
        self._manifests = list(manifests or [])
        self._mode = mode
        self._debug = debug

        # Build config
        overrides: dict = {
            "debug": debug,
            "runtime": {"mode": "test"},
            "docs_enabled": False,
        }
        if not enable_cache:
            overrides.setdefault("integrations", {})["cache"] = {"enabled": False}
        if not enable_sessions:
            overrides.setdefault("integrations", {})["sessions"] = {"enabled": False}
        if not enable_auth:
            overrides.setdefault("integrations", {})["auth"] = {"enabled": False}
        if not enable_mail:
            overrides.setdefault("integrations", {})["mail"] = {"enabled": False}
        if not enable_templates:
            overrides.setdefault("integrations", {})["templates"] = {"enabled": False}

        if config_overrides:
            overrides = _deep_merge(overrides, config_overrides)

        if config is not None:
            self._config = TestConfig(config, **overrides)
        else:
            loader = ConfigLoader()
            loader.config_data = overrides
            self._config = TestConfig(loader, **overrides)

        self._server: Optional[AquiliaServer] = None
        self._started = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> "TestServer":
        """Boot the server (idempotent)."""
        if self._started:
            return self

        # Provide a minimal manifest if none supplied
        if not self._manifests:
            self._manifests = [_empty_manifest()]

        self._server = AquiliaServer(
            manifests=self._manifests,
            config=self._config,
            mode=self._mode,
        )

        # Register with the global config registry
        set_active_config(self._config)

        await self._server.startup()
        self._started = True
        logger.info("TestServer started")
        return self

    async def stop(self) -> None:
        """Shutdown the server (idempotent)."""
        if not self._started or self._server is None:
            return
        await self._server.shutdown()
        self._started = False
        logger.info("TestServer stopped")

    # -- Async context manager -------------------------------------------

    async def __aenter__(self) -> "TestServer":
        await self.start()
        return self

    async def __aexit__(self, *exc_info):
        await self.stop()

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    @property
    def server(self) -> AquiliaServer:
        assert self._server is not None, "TestServer not started"
        return self._server

    @property
    def app(self):
        """ASGI application."""
        return self.server.app

    @property
    def config(self) -> TestConfig:
        return self._config

    @property
    def is_running(self) -> bool:
        """Whether the server is currently started."""
        return self._started

    @property
    def fault_engine(self):
        return self.server.fault_engine

    @property
    def di_container(self):
        """Return the first available DI container."""
        if self.server.runtime.di_containers:
            return next(iter(self.server.runtime.di_containers.values()))
        return None

    @property
    def controller_router(self):
        return self.server.controller_router

    @property
    def middleware_stack(self):
        return self.server.middleware_stack

    @property
    def effect_registry(self):
        return getattr(self.server, "_effect_registry", None)

    @property
    def cache_service(self):
        return getattr(self.server, "_cache_service", None)

    @property
    def session_engine(self):
        return getattr(self.server, "_session_engine", None)

    @property
    def auth_manager(self):
        return getattr(self.server, "_auth_manager", None)

    @property
    def mail_provider(self):
        return getattr(self.server, "_mail_provider", None)

    # ------------------------------------------------------------------
    # Dynamic helpers
    # ------------------------------------------------------------------

    async def reload(self) -> "TestServer":
        """Restart the server (stop + start)."""
        await self.stop()
        self._server = None
        return await self.start()

    def get_url(self, route_name: str, **params: str) -> str:
        """Reverse a named route to its URL."""
        router = self.controller_router
        if router is None:
            raise RuntimeError("No controller router available")
        return router.url_for(route_name, **params)


# -----------------------------------------------------------------------
# Convenience factory
# -----------------------------------------------------------------------

def create_test_server(
    *manifests: AppManifest,
    config_overrides: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> TestServer:
    """
    Shortcut to create a :class:`TestServer`.

    Example::

        server = create_test_server(my_manifest, debug=True)
        await server.start()
    """
    return TestServer(manifests=list(manifests), config_overrides=config_overrides, **kwargs)


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

def _empty_manifest() -> AppManifest:
    """Create a bare-minimum manifest for testing."""
    return AppManifest(
        name="test_app",
        version="0.0.1-test",
        controllers=[],
        services=[],
    )


def _deep_merge(base: dict, overrides: dict) -> dict:
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base
