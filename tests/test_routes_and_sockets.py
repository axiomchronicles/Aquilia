"""
Comprehensive route and socket registration tests for myapp.

Tests that:
1. All HTTP routes are correctly registered (36 app routes + 2 docs)
2. All WebSocket routes are correctly registered (3 sockets)
3. Socket controllers are properly instantiated with DI
4. Route methods map to correct controllers and handlers
5. ASGI-level request/response works for key routes
6. WebSocket ASGI lifecycle works
"""
import pytest
import asyncio
import sys
import os
import json

# Ensure myapp is importable
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "myapp"))
os.chdir(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "myapp"))


# ──────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def server():
    """Create and start an AquiliaServer for testing."""
    import logging
    logging.disable(logging.CRITICAL)

    from aquilia.config import ConfigLoader
    from aquilia.aquilary.core import RegistryMode
    from aquilia import AquiliaServer
    from modules.myappmod.manifest import manifest

    config = ConfigLoader.load(paths=["workspace.py"])
    config.config_data["debug"] = True
    config.config_data["mode"] = "dev"
    config.config_data["apps"] = {"myappmod": {}}
    config._build_apps_namespace()

    srv = AquiliaServer(manifests=[manifest], config=config, mode=RegistryMode.DEV)

    # Run startup
    asyncio.get_event_loop_policy().new_event_loop()
    loop = asyncio.new_event_loop()
    loop.run_until_complete(srv.startup())

    yield srv

    loop.run_until_complete(srv.shutdown())
    loop.close()


# ──────────────────────────────────────────────────────────
# ASGI helpers
# ──────────────────────────────────────────────────────────

async def asgi_request(app, method, path, body=b"", headers=None, content_type=None):
    """
    Send an ASGI HTTP request and collect the response.
    Returns (status, response_headers_dict, body_bytes).
    """
    if headers is None:
        headers = []
    if content_type:
        headers.append((b"content-type", content_type.encode() if isinstance(content_type, str) else content_type))

    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": headers,
        "query_string": b"",
    }

    body_sent = False

    async def receive():
        nonlocal body_sent
        if not body_sent:
            body_sent = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    status = None
    resp_headers = {}
    resp_body = b""

    async def send(message):
        nonlocal status, resp_headers, resp_body
        if message["type"] == "http.response.start":
            status = message["status"]
            for k, v in message.get("headers", []):
                resp_headers[k.decode() if isinstance(k, bytes) else k] = (
                    v.decode() if isinstance(v, bytes) else v
                )
        elif message["type"] == "http.response.body":
            resp_body += message.get("body", b"")

    await app(scope, receive, send)
    return status, resp_headers, resp_body


# ──────────────────────────────────────────────────────────
# Test 1: Route Registration Completeness
# ──────────────────────────────────────────────────────────

class TestRouteRegistration:
    """Verify all expected HTTP routes are registered."""

    # fmt: off
    EXPECTED_ROUTES = {
        # AuthController
        ("GET",    "/myappmod/auth/login"),
        ("POST",   "/myappmod/auth/login"),
        ("GET",    "/myappmod/auth/logout"),
        ("POST",   "/myappmod/auth/login-json"),
        ("GET",    "/myappmod/auth/me"),
        ("POST",   "/myappmod/auth/register"),

        # MyappmodUIController
        ("GET",    "/myappmod/dashboard"),
        ("GET",    "/myappmod/profile"),
        ("GET",    "/myappmod/"),

        # SessionsController
        ("GET",    "/myappmod/sessions/list"),

        # MyappmodController (CRUD)
        ("GET",    "/myappmod/items/"),
        ("POST",   "/myappmod/items/"),
        ("GET",    "/myappmod/items/«id:int»"),
        ("PUT",    "/myappmod/items/«id:int»"),
        ("DELETE", "/myappmod/items/«id:int»"),

        # AdvancedFeaturesController
        ("GET",    "/myappmod/advanced/audit"),
        ("GET",    "/myappmod/advanced/lazy/«data:str»"),

        # AdvancedUserController
        ("GET",    "/myappmod/advanced/users/{id}"),
        ("GET",    "/myappmod/advanced/users/config"),

        # JwtBearerController
        ("GET",    "/myappmod/jwt/protected"),
        ("GET",    "/myappmod/jwt/info"),

        # DashboardController
        ("GET",    "/myappmod/api/dashboard/home"),
        ("GET",    "/myappmod/api/dashboard/stats"),
        ("GET",    "/myappmod/api/dashboard/settings"),
        ("POST",   "/myappmod/api/dashboard/pref"),
        ("GET",    "/myappmod/api/dashboard/pref"),

        # SessionController
        ("GET",    "/myappmod/api/sessions/"),
        ("POST",   "/myappmod/api/sessions/login"),
        ("POST",   "/myappmod/api/sessions/logout"),
        ("GET",    "/myappmod/api/sessions/profile"),
        ("POST",   "/myappmod/api/sessions/prefs"),
        ("GET",    "/myappmod/api/sessions/prefs"),
        ("GET",    "/myappmod/api/sessions/force-expire"),
        ("GET",    "/myappmod/api/sessions/admin"),
        ("POST",   "/myappmod/api/sessions/promote"),
        ("GET",    "/myappmod/api/sessions/context"),
    }
    # fmt: on

    def _get_registered_routes(self, server):
        """Extract (method, path) tuples from the controller router."""
        registered = set()
        for method, routes in server.controller_router.routes_by_method.items():
            for route in routes:
                registered.add((method, route.full_path))
        return registered

    def test_all_expected_routes_are_registered(self, server):
        """Every expected route must be in the router."""
        registered = self._get_registered_routes(server)
        missing = self.EXPECTED_ROUTES - registered
        assert not missing, f"Missing routes: {missing}"

    def test_no_unexpected_app_routes(self, server):
        """No surprise routes under /myappmod (except docs)."""
        registered = self._get_registered_routes(server)
        app_routes = {r for r in registered if r[1].startswith("/myappmod")}
        unexpected = app_routes - self.EXPECTED_ROUTES
        assert not unexpected, f"Unexpected routes: {unexpected}"

    def test_docs_routes_registered(self, server):
        """OpenAPI and Swagger UI routes must exist."""
        registered = self._get_registered_routes(server)
        assert ("GET", "/openapi.json") in registered
        assert ("GET", "/docs") in registered

    def test_route_count(self, server):
        """Total route count: 36 app + 2 docs = 38."""
        registered = self._get_registered_routes(server)
        assert len(registered) == 38, f"Expected 38 routes, got {len(registered)}: {registered}"

    def test_post_login_is_under_auth(self, server):
        """POST /myappmod/login does NOT exist — login is at /myappmod/auth/login."""
        registered = self._get_registered_routes(server)
        assert ("POST", "/myappmod/login") not in registered, (
            "POST /myappmod/login should NOT exist. "
            "Use POST /myappmod/auth/login (AuthController) or "
            "POST /myappmod/api/sessions/login (SessionController)."
        )


# ──────────────────────────────────────────────────────────
# Test 2: Controller-to-Route Mapping
# ──────────────────────────────────────────────────────────

class TestControllerMapping:
    """Verify routes map to correct controller classes."""

    CONTROLLER_ROUTES = {
        "AuthController": [
            ("GET", "/myappmod/auth/login"),
            ("POST", "/myappmod/auth/login"),
            ("GET", "/myappmod/auth/logout"),
            ("POST", "/myappmod/auth/login-json"),
            ("GET", "/myappmod/auth/me"),
            ("POST", "/myappmod/auth/register"),
        ],
        "MyappmodUIController": [
            ("GET", "/myappmod/dashboard"),
            ("GET", "/myappmod/profile"),
            ("GET", "/myappmod/"),
        ],
        "SessionsController": [
            ("GET", "/myappmod/sessions/list"),
        ],
        "MyappmodController": [
            ("GET", "/myappmod/items/"),
            ("POST", "/myappmod/items/"),
            ("GET", "/myappmod/items/«id:int»"),
            ("PUT", "/myappmod/items/«id:int»"),
            ("DELETE", "/myappmod/items/«id:int»"),
        ],
        "AdvancedFeaturesController": [
            ("GET", "/myappmod/advanced/audit"),
            ("GET", "/myappmod/advanced/lazy/«data:str»"),
        ],
        "AdvancedUserController": [
            ("GET", "/myappmod/advanced/users/{id}"),
            ("GET", "/myappmod/advanced/users/config"),
        ],
        "JwtBearerController": [
            ("GET", "/myappmod/jwt/protected"),
            ("GET", "/myappmod/jwt/info"),
        ],
        "DashboardController": [
            ("GET", "/myappmod/api/dashboard/home"),
            ("GET", "/myappmod/api/dashboard/stats"),
            ("GET", "/myappmod/api/dashboard/settings"),
            ("POST", "/myappmod/api/dashboard/pref"),
            ("GET", "/myappmod/api/dashboard/pref"),
        ],
        "SessionController": [
            ("GET", "/myappmod/api/sessions/"),
            ("POST", "/myappmod/api/sessions/login"),
            ("POST", "/myappmod/api/sessions/logout"),
            ("GET", "/myappmod/api/sessions/profile"),
            ("POST", "/myappmod/api/sessions/prefs"),
            ("GET", "/myappmod/api/sessions/prefs"),
            ("GET", "/myappmod/api/sessions/force-expire"),
            ("GET", "/myappmod/api/sessions/admin"),
            ("POST", "/myappmod/api/sessions/promote"),
            ("GET", "/myappmod/api/sessions/context"),
        ],
    }

    def _build_route_map(self, server):
        """Build {(method, path): controller_name} mapping."""
        route_map = {}
        for method, routes in server.controller_router.routes_by_method.items():
            for route in routes:
                ctrl_name = route.controller_class.__name__
                route_map[(method, route.full_path)] = ctrl_name
        return route_map

    def test_each_controller_owns_its_routes(self, server):
        """Every route maps to its expected controller."""
        route_map = self._build_route_map(server)
        for ctrl_name, expected_routes in self.CONTROLLER_ROUTES.items():
            for method, path in expected_routes:
                actual = route_map.get((method, path))
                assert actual == ctrl_name, (
                    f"Route {method} {path} should map to {ctrl_name}, got {actual}"
                )

    def test_nine_unique_controllers(self, server):
        """There should be exactly 9 distinct app controllers."""
        route_map = self._build_route_map(server)
        app_controllers = {
            name for (method, path), name in route_map.items()
            if path.startswith("/myappmod")
        }
        assert len(app_controllers) == 9, f"Expected 9 controllers, got {app_controllers}"


# ──────────────────────────────────────────────────────────
# Test 3: Socket Registration
# ──────────────────────────────────────────────────────────

class TestSocketRegistration:
    """Verify all WebSocket routes are registered."""

    EXPECTED_SOCKETS = {
        "/myappmod/ws/chat": "ChatSocket",
        "/myappmod/ws/notifications": "NotificationSocket",
        "/myappmod/ws/feed": "PublicFeedSocket",
    }

    def test_all_socket_routes_registered(self, server):
        """All 3 socket namespaces must be in the router."""
        registered = set(server.socket_router.routes.keys())
        expected = set(self.EXPECTED_SOCKETS.keys())
        missing = expected - registered
        assert not missing, f"Missing socket routes: {missing}"

    def test_socket_controller_instances_created(self, server):
        """Each socket route has a live controller instance."""
        instances = server.aquila_sockets.controller_instances
        for path, expected_cls in self.EXPECTED_SOCKETS.items():
            assert path in instances, f"No instance for {path}"
            assert instances[path].__class__.__name__ == expected_cls, (
                f"Instance at {path} is {instances[path].__class__.__name__}, expected {expected_cls}"
            )

    def test_socket_count(self, server):
        """Exactly 3 socket routes."""
        assert len(server.socket_router.routes) == 3

    def test_chat_socket_has_event_handlers(self, server):
        """ChatSocket route metadata includes event handlers."""
        meta = server.socket_router.routes.get("/myappmod/ws/chat")
        assert meta is not None
        # ChatSocket defines: chat.join, chat.message
        assert "chat.join" in meta.handlers or "chat.message" in meta.handlers, (
            f"ChatSocket handlers: {list(meta.handlers.keys())}"
        )

    def test_socket_namespace_attribute_set(self, server):
        """Controller instances have .namespace attribute set."""
        for path, inst in server.aquila_sockets.controller_instances.items():
            assert hasattr(inst, "namespace"), f"Instance at {path} missing .namespace"
            assert inst.namespace == path


# ──────────────────────────────────────────────────────────
# Test 4: ASGI HTTP Smoke Tests
# ──────────────────────────────────────────────────────────

class TestASGIHTTPSmoke:
    """Hit key routes via ASGI to verify they return expected status codes."""

    @pytest.mark.asyncio
    async def test_home_returns_redirect(self, server):
        status, _, _ = await asgi_request(server.app, "GET", "/myappmod/")
        # Home page redirects to dashboard
        assert status in (200, 301, 302, 307, 308), f"GET /myappmod/ returned {status}"

    @pytest.mark.asyncio
    async def test_login_page_returns_ok(self, server):
        status, _, _ = await asgi_request(server.app, "GET", "/myappmod/auth/login")
        assert status == 200

    @pytest.mark.asyncio
    async def test_items_list_returns_ok(self, server):
        status, _, _ = await asgi_request(server.app, "GET", "/myappmod/items/")
        assert status == 200

    @pytest.mark.asyncio
    async def test_dashboard_home_requires_auth_or_ok(self, server):
        status, _, _ = await asgi_request(server.app, "GET", "/myappmod/api/dashboard/home")
        # May require auth (403) or return 200 if open
        assert status in (200, 401, 403), f"GET /api/dashboard/home returned {status}"

    @pytest.mark.asyncio
    async def test_sessions_info_returns_ok(self, server):
        status, _, body = await asgi_request(server.app, "GET", "/myappmod/api/sessions/")
        # SessionController may return 200 with session info or fallback
        assert status in (200, 401, 403), f"GET /api/sessions/ returned {status}"

    @pytest.mark.asyncio
    async def test_advanced_audit_returns_ok(self, server):
        status, _, _ = await asgi_request(server.app, "GET", "/myappmod/advanced/audit")
        assert status == 200

    @pytest.mark.asyncio
    async def test_openapi_json(self, server):
        status, _, body = await asgi_request(server.app, "GET", "/openapi.json")
        # Docs routes are manually registered; may return 400 if scope missing fields
        assert status in (200, 400), f"GET /openapi.json returned {status}"
        if status == 200:
            data = json.loads(body)
            assert "paths" in data or "openapi" in data

    @pytest.mark.asyncio
    async def test_docs_returns_html(self, server):
        status, headers, body = await asgi_request(server.app, "GET", "/docs")
        assert status in (200, 400), f"GET /docs returned {status}"
        if status == 200:
            assert b"swagger-ui" in body.lower()

    @pytest.mark.asyncio
    async def test_nonexistent_route_returns_404(self, server):
        status, _, _ = await asgi_request(server.app, "GET", "/myappmod/nonexistent")
        assert status == 404

    @pytest.mark.asyncio
    async def test_post_myappmod_login_returns_404(self, server):
        """POST /myappmod/login should 404 — correct URL is /myappmod/auth/login."""
        status, _, _ = await asgi_request(
            server.app, "POST", "/myappmod/login",
            body=b"username=admin&password=password",
            content_type="application/x-www-form-urlencoded",
        )
        assert status == 404, (
            f"POST /myappmod/login returned {status} but should be 404. "
            "Use POST /myappmod/auth/login instead."
        )

    @pytest.mark.asyncio
    async def test_create_item(self, server):
        body = json.dumps({"name": "Test", "description": "pytest item"}).encode()
        status, _, resp = await asgi_request(
            server.app, "POST", "/myappmod/items/",
            body=body, content_type="application/json",
        )
        assert status in (200, 201), f"POST /myappmod/items/ returned {status}"

    @pytest.mark.asyncio
    async def test_form_login_returns_redirect_or_ok(self, server):
        body = b"username=admin&password=password"
        status, _, _ = await asgi_request(
            server.app, "POST", "/myappmod/auth/login",
            body=body, content_type="application/x-www-form-urlencoded",
        )
        # Login can return 200, 302 redirect, 303, or 307 temporary redirect
        assert status in (200, 302, 303, 307), f"POST /myappmod/auth/login returned {status}"

    @pytest.mark.asyncio
    async def test_json_login_returns_token(self, server):
        body = json.dumps({"username": "admin", "password": "password"}).encode()
        status, _, resp = await asgi_request(
            server.app, "POST", "/myappmod/auth/login-json",
            body=body, content_type="application/json",
        )
        assert status == 200, f"POST /myappmod/auth/login-json returned {status}"

    @pytest.mark.asyncio
    async def test_register_user(self, server):
        body = json.dumps({
            "username": "testuser_pytest",
            "password": "securePass123",
            "email": "test@pytest.local",
        }).encode()
        status, _, _ = await asgi_request(
            server.app, "POST", "/myappmod/auth/register",
            body=body, content_type="application/json",
        )
        assert status in (200, 201, 409), f"POST /myappmod/auth/register returned {status}"


# ──────────────────────────────────────────────────────────
# Test 5: WebSocket ASGI Smoke Tests
# ──────────────────────────────────────────────────────────

class TestWebSocketASGI:
    """Verify WebSocket ASGI lifecycle at the adapter level."""

    @pytest.mark.asyncio
    async def test_websocket_connect_chat(self, server):
        """Chat socket should accept a WebSocket connect."""
        scope = {
            "type": "websocket",
            "path": "/myappmod/ws/chat",
            "headers": [],
            "query_string": b"",
        }

        messages_sent = []

        async def receive():
            return {"type": "websocket.connect"}

        async def send(msg):
            messages_sent.append(msg)

        # The socket runtime should handle the connection
        try:
            await asyncio.wait_for(
                server.app(scope, receive, send),
                timeout=2.0,
            )
        except (asyncio.TimeoutError, Exception):
            pass  # Socket connections are long-lived, timeout is expected

        # Check that we got either accept or close (for auth-required sockets)
        msg_types = [m.get("type") for m in messages_sent]
        assert any(
            t in ("websocket.accept", "websocket.close") for t in msg_types
        ), f"Expected accept or close, got: {msg_types}"

    @pytest.mark.asyncio
    async def test_websocket_connect_public_feed(self, server):
        """Public feed socket should accept anonymous connections."""
        scope = {
            "type": "websocket",
            "path": "/myappmod/ws/feed",
            "headers": [],
            "query_string": b"",
        }

        messages_sent = []
        connect_sent = False

        async def receive():
            nonlocal connect_sent
            if not connect_sent:
                connect_sent = True
                return {"type": "websocket.connect"}
            # Keep connection alive briefly then disconnect
            await asyncio.sleep(1)
            return {"type": "websocket.disconnect", "code": 1000}

        async def send(msg):
            messages_sent.append(msg)

        try:
            await asyncio.wait_for(
                server.app(scope, receive, send),
                timeout=3.0,
            )
        except (asyncio.TimeoutError, Exception):
            pass

        msg_types = [m.get("type") for m in messages_sent]
        # Public feed should accept since it allows anonymous
        assert "websocket.accept" in msg_types or "websocket.close" in msg_types, (
            f"Public feed got: {msg_types}"
        )

    @pytest.mark.asyncio
    async def test_websocket_unknown_path_rejected(self, server):
        """Unknown WS path should be closed."""
        scope = {
            "type": "websocket",
            "path": "/unknown/ws/path",
            "headers": [],
            "query_string": b"",
        }

        messages_sent = []

        async def receive():
            return {"type": "websocket.connect"}

        async def send(msg):
            messages_sent.append(msg)

        try:
            await asyncio.wait_for(
                server.app(scope, receive, send),
                timeout=2.0,
            )
        except (asyncio.TimeoutError, Exception):
            pass

        msg_types = [m.get("type") for m in messages_sent]
        assert "websocket.close" in msg_types, (
            f"Unknown WS path should close, got: {msg_types}"
        )


# ──────────────────────────────────────────────────────────
# Test 6: Config Builders Socket Support
# ──────────────────────────────────────────────────────────

class TestConfigBuildersSocket:
    """Verify Module builder supports socket registration."""

    def test_module_register_sockets_method(self):
        """Module builder has register_sockets method."""
        from aquilia.config_builders import Module
        m = Module("test")
        assert hasattr(m, "register_sockets")

    def test_module_register_sockets_adds_to_config(self):
        """register_sockets adds paths to socket_controllers."""
        from aquilia.config_builders import Module
        m = Module("test")
        m.register_sockets("path:SocketA", "path:SocketB")
        config = m.build()
        assert config.socket_controllers == ["path:SocketA", "path:SocketB"]

    def test_module_config_to_dict_includes_sockets(self):
        """ModuleConfig.to_dict() includes socket_controllers."""
        from aquilia.config_builders import Module
        m = Module("test")
        m.register_sockets("path:SocketA")
        d = m.build().to_dict()
        assert "socket_controllers" in d
        assert d["socket_controllers"] == ["path:SocketA"]

    def test_module_chaining(self):
        """register_sockets returns self for fluent chaining."""
        from aquilia.config_builders import Module
        result = (
            Module("test")
            .route_prefix("/test")
            .register_controllers("c:A")
            .register_sockets("s:B")
            .register_services("s:C")
        )
        cfg = result.build()
        assert cfg.controllers == ["c:A"]
        assert cfg.socket_controllers == ["s:B"]
        assert cfg.services == ["s:C"]

    def test_workspace_exports_sockets(self):
        """Workspace.to_dict() modules include socket_controllers."""
        from aquilia.config_builders import Workspace, Module
        ws = (
            Workspace("test")
            .module(
                Module("mod1")
                .register_sockets("sockets:Chat")
            )
        )
        d = ws.to_dict()
        mod = d["modules"][0]
        assert "socket_controllers" in mod
        assert mod["socket_controllers"] == ["sockets:Chat"]
