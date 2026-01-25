#!/usr/bin/env python3
"""
Session Integration Test

This demonstrates the deep session integration with Aquilia's core components.
"""

import asyncio
from aquilia import AquiliaServer, Controller, GET, POST, RequestCtx, Response
from aquilia.sessions import SessionPolicy, SessionEngine, MemoryStore, CookieTransport, TransportPolicy
from aquilia.sessions.decorators import session, authenticated
from aquilia.config import ConfigLoader
from aquilia.manifest import AppManifest
from datetime import timedelta


class SessionTestController(Controller):
    """Test controller demonstrating deep session integration."""
    
    @GET("/test/session-info")
    @session.optional()
    async def session_info(self, ctx: RequestCtx):
        """Test endpoint showing session information."""
        return Response.json({
            "has_request": hasattr(ctx, 'request'),
            "has_session": hasattr(ctx, 'session'),
            "session_exists": ctx.session is not None,
            "session_id": str(ctx.session.id) if ctx.session else None,
            "session_authenticated": ctx.session.is_authenticated if ctx.session else False,
            "request_state_has_session": ctx.request.state.get('session') is not None,
            "ctx_type": str(type(ctx)),
        })
    
    @POST("/test/create-session")
    @session.ensure()
    async def create_session(self, ctx: RequestCtx):
        """Test endpoint that ensures session creation."""
        return Response.json({
            "message": "Session ensured",
            "session_id": str(ctx.session.id),
            "created_at": ctx.session.created_at.isoformat(),
        })
    
    @GET("/test/require-session")
    @session.require()
    async def require_session(self, ctx: RequestCtx):
        """Test endpoint that requires session."""
        return Response.json({
            "message": "Session required and available",
            "session_id": str(ctx.session.id),
        })


async def test_session_integration():
    """Test the deep session integration."""
    
    print("🧪 Testing Deep Session Integration")
    print("=" * 60)
    
    # Create configuration with sessions enabled
    config = ConfigLoader()
    config.config_data = {
        "sessions": {
            "enabled": True,
            "policy": {
                "name": "test_session",
                "ttl_days": 1,
                "idle_timeout_minutes": 30,
            },
            "store": {
                "type": "memory",
                "max_sessions": 1000,
            },
            "transport": {
                "adapter": "cookie",
                "cookie_name": "test_session",
                "cookie_secure": False,  # For testing
                "cookie_httponly": True,
            },
        }
    }
    
    # Create manifest with test controller
    class TestManifest(AppManifest):
        controllers = ["__main__:SessionTestController"]
    
    manifest = TestManifest("test", "1.0.0")
    
    # Create server with session integration
    server = AquiliaServer(
        manifests=[manifest],
        config=config,
    )
    
    print("✅ Server created with session integration")
    print(f"Session config: {config.get_session_config()}")
    
    # Test would continue with actual HTTP requests...
    print("✅ Session integration test setup complete!")
    print("\nTo run full test:")
    print("1. Start server: server.run()")
    print("2. Test endpoints:")
    print("   GET  /test/session-info     - Check session status")
    print("   POST /test/create-session   - Ensure session creation")
    print("   GET  /test/require-session  - Test session requirement")
    
    return server


if __name__ == "__main__":
    server = asyncio.run(test_session_integration())
    print("\n🚀 Starting server with deep session integration...")
    server.run(host="127.0.0.1", port=8080, reload=True)