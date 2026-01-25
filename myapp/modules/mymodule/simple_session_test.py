# ============================================================================
# Simple Session Test Controller
# ============================================================================

from aquilia.controller import Controller, RequestCtx
from aquilia.controller.decorators import GET, POST
from aquilia import session
import json
import time


class SimpleSessionTestController(Controller):
    """Simple controller for testing session functionality."""
    
    prefix = "/session-test"
    tags = ["session-test"]
    
    def __init__(self):
        self.controller_name = "SimpleSessionTest"
    
    @GET("/info")
    async def session_info(self, ctx: RequestCtx):
        """Get current session information."""
        sess = session.current()
        
        if not sess:
            return {"session": None, "message": "No session found"}
        
        return {
            "session": {
                "id": sess.id,
                "principal": sess.principal.__dict__ if sess.principal else None,
                "metadata": sess.metadata,
                "expires_at": str(sess.expires_at) if sess.expires_at else None
            }
        }
    
    @POST("/login")
    async def test_login(self, ctx: RequestCtx):
        """Test session login functionality."""
        # Create a test session
        sess = session.create()
        
        # Set authentication data
        sess.principal.username = "testuser"
        sess.principal.email = "test@example.com"
        sess.principal.authenticated = True
        sess.principal.roles = ["user"]
        
        # Save session
        await sess.save()
        
        return {
            "message": "Login successful",
            "session_id": sess.id,
            "principal": sess.principal.__dict__
        }
    
    @POST("/logout")
    async def test_logout(self, ctx: RequestCtx):
        """Test session logout functionality."""
        sess = session.current()
        
        if not sess:
            return {"message": "No session to logout"}
        
        # Clear session
        await sess.destroy()
        
        return {"message": "Logout successful"}
    
    @GET("/protected")
    @session.require()
    async def protected_endpoint(self, ctx: RequestCtx):
        """Test protected endpoint requiring session."""
        sess = session.current()
        
        return {
            "message": "Access granted to protected resource",
            "user": sess.principal.username if sess.principal else "unknown",
            "roles": sess.principal.roles if sess.principal else []
        }
    
    @GET("/data")
    async def session_data_test(self, ctx: RequestCtx):
        """Test session data storage and retrieval."""
        sess = session.current()
        
        if not sess:
            sess = session.create()
            await sess.save()
        
        # Store some test data
        sess.data["test_key"] = "test_value"
        sess.data["timestamp"] = time.time()
        sess.data["counter"] = sess.data.get("counter", 0) + 1
        
        await sess.save()
        
        return {
            "session_data": sess.data,
            "data_size": len(str(sess.data))
        }