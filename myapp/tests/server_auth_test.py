
import pytest
import asyncio
from aquilia.server import AquiliaServer, RegistryMode
from aquilia.config import ConfigLoader
from aquilia.manifest import AppManifest
from aquilia.controller import Controller, GET
from aquilia.response import Response, Ok
from aquilia.auth.integration.flow_guards import RequireAuthGuard
from aquilia.auth.core import Identity

# Define a controller for testing
class AuthTestController(Controller):
    @GET("/public")
    async def public(self, ctx):
        return Ok({"status": "public"})
    
    @GET("/protected", pipeline=[RequireAuthGuard()])
    async def protected(self, ctx, identity: Identity):
        return Ok({"user": identity.id})

# Define a manifest
class AuthTestApp(AppManifest):
    name = "test_auth_app"
    version = "1.0.0"
    controllers = ["myapp.tests.server_auth_test:AuthTestController"]

def test_server_auth_integration():
    asyncio.run(_test_body())

async def _test_body():
    # 1. Setup Config with Auth Enabled
    config = ConfigLoader()
    config._merge_dict(config.config_data, {
        "auth": {
            "enabled": True,
            "tokens": {
                "secret_key": "test_secret_key_12345",
                "issuer": "test_issuer"
            }
        },
        "sessions": {
            "enabled": True, # Implicitly required but good to be explicit
            "store": {"type": "memory"}
        }
    })
    config._build_apps_namespace()
    
    # 2. Create Server
    # We need to make sure the controller is importable. 
    # Since we are running from pytest, we assume myapp is in path or we set PYTHONPATH.
    # But specifically, "myapp.tests.server_auth_test" needs to resolve to THIS file.
    
    server = AquiliaServer(
        manifests=[AuthTestApp],
        config=config,
        mode=RegistryMode.TEST
    )
    
    # 3. Startup Server
    await server.startup()
    
    try:
        # 4. Verify DI Registration
        # Get the app container
        app_container = server.runtime.di_containers["test_auth_app"]
        from aquilia.auth.manager import AuthManager
        from aquilia.sessions import SessionEngine
        
        auth_manager = await app_container.resolve_async(AuthManager)
        session_engine = await app_container.resolve_async(SessionEngine)
        
        assert auth_manager is not None
        assert session_engine is not None
        
        # 5. Verify Middleware Stack
        # Check if 'auth' middleware is present
        middleware_names = [mw.name for mw in server.middleware_stack.middlewares]
        assert "auth" in middleware_names
        assert "session" not in middleware_names # Should be replaced by auth
        
        # 6. Test Request Flow
        # Use server.app (ASGI Adapter) to simulate request
        
        # 6a. Public Endpoint
        scope_public = {
            "type": "http",
            "method": "GET",
            "path": "/public",
            "headers": [],
            "query_string": b"",
        }
        
        async def receive():
            return {"type": "http.request", "body": b""}
        
        response_body = b""
        async def send(message):
            nonlocal response_body
            if message["type"] == "http.response.body":
                response_body += message.get("body", b"")
        
        await server.app(scope_public, receive, send)
        assert b'"status": "public"' in response_body
        
        # 6b. Protected Endpoint (Unauthenticated)
        scope_protected = {
            "type": "http",
            "method": "GET",
            "path": "/protected",
            "headers": [],
            "query_string": b"",
        }
        
        response_status = 0
        async def send_protected(message):
            nonlocal response_status
            if message["type"] == "http.response.start":
                response_status = message["status"]
                
        await server.app(scope_protected, receive, send_protected)
        assert response_status == 403
        
        # 6c. Protected Endpoint (Authenticated)
        # Create a valid token and save identity
        identity = Identity(id="user_test", type="user", attributes={})
        await auth_manager.identity_store.create(identity)
        
        token = await auth_manager.token_manager.issue_access_token(
            identity_id=identity.id,
            scopes=["profile"],
            roles=[]
        )
        
        # Verify token immediately
        fetched_identity = await auth_manager.get_identity_from_token(token)
        assert fetched_identity is not None, "Token validation failed in test setup"
        assert fetched_identity.id == identity.id
        
        scope_auth = {
            "type": "http",
            "method": "GET",
            "path": "/protected",
            "headers": [
                (b"authorization", f"Bearer {token}".encode())
            ],
            "query_string": b"",
        }
        
        response_body_auth = b""
        response_status_auth = 0
        async def send_auth(message):
            nonlocal response_body_auth, response_status_auth
            if message["type"] == "http.response.start":
                response_status_auth = message["status"]
            if message["type"] == "http.response.body":
                response_body_auth += message.get("body", b"")
                
        await server.app(scope_auth, receive, send_auth)
        assert response_status_auth == 200
        assert b'"user": "user_test"' in response_body_auth
        
    finally:
        await server.shutdown()
