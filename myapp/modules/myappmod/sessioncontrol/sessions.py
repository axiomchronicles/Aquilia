from typing import List
from aquilia import Controller, GET, POST, DELETE, RequestCtx, Response
from aquilia.sessions import SessionPrincipal, session, authenticated, stateful
from aquilia.sessions.state import SessionState, Field
from aquilia.sessions.enhanced import requires, AdminGuard

class UserPrefs(SessionState):
    """Typed session state for user preferences."""
    theme: str = Field(default="light")
    notifications: bool = Field(default=True)
    last_visited: str = Field(default="")

class SessionController(Controller):
    """
    Demonstrates the full range of Aquilia session features.
    
    Includes:
    - Manual principal binding
    - @authenticated decorator for identity protection
    - @stateful decorator for typed state management
    - Concurrency and expiration handling
    """
    prefix = "/sessions"
    
    @GET("/")
    async def get_session_info(self, ctx: RequestCtx):
        """Get information about the current session."""
        sess = ctx.session
        return {
            "session_id": str(sess.id),
            "is_authenticated": sess.is_authenticated,
            "principal": {
                "kind": sess.principal.kind,
                "id": sess.principal.id,
                "attributes": sess.principal.attributes
            } if sess.principal else None,
            "data": sess.data,
            "expires_at": sess.expires_at.isoformat() if sess.expires_at else None,
        }

    @POST("/login")
    async def login(self, ctx: RequestCtx):
        """Log in a user by creating a principal and binding it to the session."""
        data = await ctx.json()
        user_id = data.get("user_id", "test_user")
        
        principal = SessionPrincipal(
            kind="user",
            id=user_id,
            attributes={
                "role": "member", 
                "email": f"{user_id}@example.com",
                "login_time": str(ctx.request.state.get("request_id", "unknown"))
            }
        )
        
        # Bind principal to current session (this triggers rotation if configured)
        ctx.session.mark_authenticated(principal)
        
        return {
            "message": f"Logged in as {user_id}", 
            "session_id": str(ctx.session.id)
        }

    @POST("/logout")
    @authenticated
    async def logout(self, ctx: RequestCtx):
        """Log out the current user by clearing authentication."""
        ctx.session.clear_authentication()
        return {"message": "Successfully logged out"}

    @GET("/profile")
    @authenticated
    async def profile(self, ctx: RequestCtx, user: SessionPrincipal):
        """Protected endpoint that requires authentication."""
        return {
            "message": "Welcome to your protected profile",
            "user_id": user.id,
            "attributes": user.attributes,
            "session_data": ctx.session.data
        }

    @POST("/prefs")
    @stateful
    async def update_prefs(self, ctx: RequestCtx, state: UserPrefs):
        """Update user preferences using @stateful and typed SessionState."""
        data = await ctx.json()
        
        if "theme" in data:
            state.theme = data["theme"]
        if "notifications" in data:
            state.notifications = data["notifications"]
        
        import datetime
        state.last_visited = datetime.datetime.now().isoformat()
        
        return {
            "message": "Preferences persisted in session", 
            "current_state": {
                "theme": state.theme,
                "notifications": state.notifications,
                "last_visited": state.last_visited
            }
        }

    @GET("/prefs")
    @stateful
    async def get_prefs(self, ctx: RequestCtx, state: UserPrefs):
        """Read user preferences from the session state."""
        return {
            "theme": state.theme,
            "notifications": state.notifications,
            "last_visited": state.last_visited
        }

    @GET("/force-expire")
    async def force_expire(self, ctx: RequestCtx):
        """Utility to test session expiration."""
        import datetime
        ctx.session.expires_at = datetime.datetime.utcnow() - datetime.timedelta(seconds=1)
        return {"message": "Session marked as expired"}

    @GET("/admin")
    @authenticated
    @requires(AdminGuard())
    async def admin_only(self, ctx: RequestCtx, user: SessionPrincipal):
        """Admin only endpoint using @requires(AdminGuard())."""
        return {"message": "Hello Admin", "user_id": user.id}

    @POST("/promote")
    @authenticated
    async def promote(self, ctx: RequestCtx):
        """Promote user to admin for testing guards."""
        ctx.session.principal.attributes["role"] = "admin"
        ctx.session.mark_dirty()
        return {"message": "You are now an admin"}

    @GET("/context")
    async def test_context(self, ctx: RequestCtx):
        """Test SessionContext managers."""
        from aquilia.sessions.enhanced import SessionContext
        
        async with SessionContext.ensure(ctx) as sess:
            sess.set("context_test", "passed")
            
        try:
            async with SessionContext.transactional(ctx) as sess:
                sess.set("transaction", "failed")
                raise ValueError("rollback")
        except ValueError:
            pass
            
        return {
            "context_test": ctx.session.get("context_test"),
            "transaction_rolled_back": "transaction" not in ctx.session.data
        }