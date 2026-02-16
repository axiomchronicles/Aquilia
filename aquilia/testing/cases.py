"""
Aquilia Testing - Test Case Base Classes.

Provides Django-style test case classes with automatic server lifecycle,
DI container management, and integrated assertion helpers.
"""

from __future__ import annotations

import asyncio
import logging
import unittest
from typing import Any, Dict, List, Optional, Sequence, Type

from aquilia.manifest import AppManifest

from .assertions import AquiliaAssertions
from .client import TestClient, TestResponse
from .server import TestServer


logger = logging.getLogger("aquilia.testing.cases")


class SimpleTestCase(unittest.TestCase, AquiliaAssertions):
    """
    Test case that does NOT start a server.

    Use for pure unit tests that only need assertion helpers
    and utility functions — no DI, no ASGI, no lifecycle.

    Usage::

        class TestUtils(SimpleTestCase):
            def test_my_helper(self):
                result = my_func()
                self.assertEqual(result, 42)
    """
    pass


class AquiliaTestCase(unittest.IsolatedAsyncioTestCase, AquiliaAssertions):
    """
    Full-featured async test case with integrated server lifecycle.

    Boots a :class:`TestServer` before each test and tears it down
    afterwards.  Provides a :attr:`client` (:class:`TestClient`) wired
    to the server's ASGI app.

    Subclass attributes:
        manifests:        List of :class:`AppManifest` to load.
        settings:         Dict of config overrides.
        enable_cache:     Boot the cache subsystem (default ``False``).
        enable_sessions:  Boot sessions (default ``False``).
        enable_auth:      Boot the auth subsystem (default ``False``).
        enable_mail:      Boot mail (default ``False``).
        enable_templates: Boot templates (default ``False``).

    Usage::

        class TestUsers(AquiliaTestCase):
            manifests = [users_manifest]
            settings = {"debug": True}

            async def test_list_users(self):
                resp = await self.client.get("/users")
                self.assert_status(resp, 200)
                self.assert_json(resp)
    """

    # ── Overridable class-level config ──────────────────────────────
    manifests: List[AppManifest] = []
    settings: Dict[str, Any] = {}
    enable_cache: bool = False
    enable_sessions: bool = False
    enable_auth: bool = False
    enable_mail: bool = False
    enable_templates: bool = False

    # ── Internal state ─────────────────────────────────────────────
    server: TestServer
    client: TestClient

    # ── Lifecycle ──────────────────────────────────────────────────

    async def asyncSetUp(self) -> None:
        """Boot the test server and create a client."""
        await super().asyncSetUp()
        self.server = TestServer(
            manifests=self.manifests or None,
            config_overrides=self.settings,
            enable_cache=self.enable_cache,
            enable_sessions=self.enable_sessions,
            enable_auth=self.enable_auth,
            enable_mail=self.enable_mail,
            enable_templates=self.enable_templates,
        )
        await self.server.start()
        self.client = TestClient(self.server)

    async def asyncTearDown(self) -> None:
        """Shutdown the test server."""
        await self.server.stop()
        await super().asyncTearDown()

    # ── Convenience accessors ──────────────────────────────────────

    @property
    def di_container(self):
        return self.server.di_container

    @property
    def fault_engine(self):
        return self.server.fault_engine

    @property
    def config(self):
        return self.server.config

    @property
    def controller_router(self):
        return self.server.controller_router

    @property
    def effect_registry(self):
        return self.server.effect_registry

    @property
    def cache_service(self):
        return self.server.cache_service

    # ── Helper methods ─────────────────────────────────────────────

    def get_url(self, route_name: str, **params: str) -> str:
        """Reverse a named route to its URL."""
        try:
            return self.controller_router.url_for(route_name, **params)
        except Exception:
            raise ValueError(f"Cannot reverse route {route_name!r}")

    async def login(
        self,
        username: str = "test@test.com",
        password: str = "password",
    ) -> TestResponse:
        """
        Convenience login helper.

        Issues a POST to ``/auth/login`` (the conventional Aquilia auth
        endpoint).  Override this method if your app uses a different URL.
        """
        return await self.client.post(
            "/auth/login",
            json={"username": username, "password": password},
        )


class TransactionTestCase(AquiliaTestCase):
    """
    Test case that wraps each test in a database transaction.

    The transaction is rolled back after the test completes, so database
    state is never committed — tests are fully isolated.

    Requires ``database.url`` in settings and an active DB connection.

    Usage::

        class TestProductCRUD(TransactionTestCase):
            manifests = [products_manifest]
            settings = {"database": {"url": "sqlite:///test.db", "auto_create": True}}

            async def test_create_product(self):
                resp = await self.client.post("/products", json={"name": "Widget"})
                self.assert_status(resp, 201)
    """

    _transaction: Any = None

    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()
        # Start a DB transaction if database is available
        db = getattr(self.server.server, "_amdl_database", None)
        if db and hasattr(db, "begin"):
            self._transaction = await db.begin()

    async def asyncTearDown(self) -> None:
        # Rollback the transaction
        if self._transaction is not None:
            try:
                await self._transaction.rollback()
            except Exception:
                pass
        await super().asyncTearDown()


class LiveServerTestCase(AquiliaTestCase):
    """
    Test case that starts a real ASGI server on a random port.

    Useful for end-to-end tests that need a genuine TCP connection
    (e.g., testing with an HTTP library or browser automation).

    The bound address is available via :attr:`live_server_url`.

    Usage::

        class TestE2E(LiveServerTestCase):
            manifests = [app_manifest]

            async def test_healthcheck(self):
                import httpx
                async with httpx.AsyncClient() as http:
                    resp = await http.get(f"{self.live_server_url}/health")
                    assert resp.status_code == 200
    """

    host: str = "127.0.0.1"
    port: int = 0  # 0 = random port

    _uvicorn_server: Any = None
    _serve_task: Optional[asyncio.Task] = None
    live_server_url: str = ""

    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()
        await self._start_live_server()

    async def asyncTearDown(self) -> None:
        await self._stop_live_server()
        await super().asyncTearDown()

    async def _start_live_server(self) -> None:
        try:
            import uvicorn
        except ImportError:
            self.skipTest("uvicorn required for LiveServerTestCase")
            return

        config = uvicorn.Config(
            self.server.app,
            host=self.host,
            port=self.port,
            log_level="error",
        )
        self._uvicorn_server = uvicorn.Server(config)

        self._serve_task = asyncio.create_task(self._uvicorn_server.serve())
        # Wait for server to be ready
        for _ in range(100):
            if self._uvicorn_server.started:
                break
            await asyncio.sleep(0.05)

        # Determine actual bound port
        sockets = self._uvicorn_server.servers
        if sockets:
            sock = list(sockets)[0].sockets[0]
            actual_port = sock.getsockname()[1]
        else:
            actual_port = self.port
        self.live_server_url = f"http://{self.host}:{actual_port}"

    async def _stop_live_server(self) -> None:
        if self._uvicorn_server:
            self._uvicorn_server.should_exit = True
        if self._serve_task:
            try:
                await asyncio.wait_for(self._serve_task, timeout=3.0)
            except (asyncio.TimeoutError, Exception):
                self._serve_task.cancel()
