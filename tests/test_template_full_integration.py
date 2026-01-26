import pytest
import asyncio
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from aquilia.server import AquiliaServer
from aquilia.manifest import AppManifest, TemplateConfig, SessionConfig, FaultHandlingConfig
from aquilia.controller.base import Controller, RequestCtx
from aquilia.controller.decorators import GET
from aquilia.di.decorators import service
from aquilia.config import ConfigLoader
from aquilia.response import Response
from aquilia.sessions import SessionEngine, MemoryStore

from aquilia.templates.sessions_integration import TemplateFlashMixin

class TestController(Controller, TemplateFlashMixin):
    prefix = "/test-templates"
    
    @GET("/render")
    async def render_test(self, ctx: RequestCtx):
        # Create template engine manually for now
        from aquilia.templates import TemplateEngine
        from aquilia.templates.loader import TemplateLoader
        from pathlib import Path
        
        # Create loader
        search_paths = [Path("tests/test_templates")]
        loader = TemplateLoader(search_paths=search_paths)
        
        # Create engine
        engine = TemplateEngine(loader=loader)
        
        # Add a flash message
        if hasattr(self, "flash"):
            from aquilia.templates.sessions_integration import TemplateFlashMixin
            if isinstance(self, TemplateFlashMixin):
                self.flash(ctx, "Hello Flash!", "success")
        
        return self.render("test.html", {"val": "World"}, ctx, engine=engine)

class TestTemplateManifest(AppManifest):
    name = "test_templates_app"
    version = "1.0.0"
    controllers = ["tests.test_template_full_integration:TestController"]
    
    templates = TemplateConfig(
        enabled=True,
        search_paths=["tests/test_templates"]
    )
    
    sessions = [SessionConfig(name="default", enabled=True, store="memory")]

@pytest.fixture
def server():
    config = ConfigLoader()
    # Enable sessions and auth in config for global middleware
    config.config_data["sessions"] = {"enabled": True}
    config.config_data["auth"] = {"enabled": True}
    
    # We need to hack a bit because create_auth_manager expects some keys
    config.config_data["auth"]["tokens"] = {"secret_key": "test_secret"}
    
    server = AquiliaServer(
        manifests=[TestTemplateManifest],
        config=config
    )
    return server

@pytest.mark.asyncio
async def test_template_full_integration(server):
    await server.startup()
    app = server.app
    
    # We'll patch the auth manager to return our mock identity
    from aquilia.auth.integration.middleware import AquilAuthMiddleware
    from aquilia.auth.core import Identity, IdentityType
    
    identity = Identity(
        id="user123",
        type=IdentityType.USER,
        attributes={"username": "testuser", "roles": {"admin"}}
    )
    
    # Patch the auth manager to return our identity
    async def mock_get_identity_from_token(token):
        return identity
    
    # Find the auth manager in the middleware
    auth_middleware = None
    for descriptor in server.middleware_stack.middlewares:
        mw = descriptor.middleware
        if isinstance(mw, AquilAuthMiddleware):
            auth_middleware = mw
            break
    
    if auth_middleware:
        original_get_identity = auth_middleware.auth_manager.get_identity_from_token
        auth_middleware.auth_manager.get_identity_from_token = mock_get_identity_from_token
        
        # Also mock the identity store
        async def mock_identity_store_get(identity_id):
            if identity_id == "user123":
                return identity
            return None
        
        original_store_get = auth_middleware.auth_manager.identity_store.get
        auth_middleware.auth_manager.identity_store.get = mock_identity_store_get
    
    try:
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test-templates/render",
            "headers": [(b"authorization", b"Bearer test_token")],  # Add auth header with mock token
            "query_string": b"",
            "state": {}
        }
        
        async def receive():
            return {"type": "http.request", "body": b""}
        
        responses = []
        async def send(message):
            responses.append(message)
        
        # Pre-populate request state via the middleware stack or manually for the test
        # Actually, we want to test that the middleware INJECTS these.
        
        scope["state"]["app_name"] = "test_templates_app"
        await app(scope, receive, send)
        
        # Debugging: print responses if assertion fails
        if not any(resp.get("type") == "http.response.start" and resp.get("status") == 200 for resp in responses):
            print(f"FAILED: No 200 response found. Total responses: {len(responses)}")
            for i, resp in enumerate(responses):
                print(f"Response {i}: {resp}")
        
        # Verify response
        assert any(resp["type"] == "http.response.start" and resp["status"] == 200 for resp in responses)
        
        body_msg = next(resp for resp in responses if resp["type"] == "http.response.body")
        body = body_msg["body"].decode()
        
        assert "Hello World!" in body
        assert "Request path: /test-templates/render" in body
        assert "User: testuser" in body
        assert "Auth: True" in body
        assert "Has Admin: True" in body
        assert "Session ID:" in body
        # Flash message check
        assert "success: Hello Flash!" in body
        
    finally:
        if auth_middleware:
            auth_middleware.auth_manager.get_identity_from_token = original_get_identity
            auth_middleware.auth_manager.identity_store.get = original_store_get
        await server.shutdown()

if __name__ == "__main__":
    # Manual run
    import sys
    async def run_test():
        loader = ConfigLoader()
        s = server()
        await test_template_full_integration(s)
    
    asyncio.run(run_test())
