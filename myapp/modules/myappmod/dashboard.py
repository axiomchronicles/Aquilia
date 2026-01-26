from aquilia.controller import Controller, GET, POST, RequestCtx
from aquilia.response import Response
from aquilia.sessions.decorators import authenticated, stateful
from aquilia.auth.core import Identity
from typing import Any, Optional
import logging

logger = logging.getLogger("myapp.dashboard")

class DashboardController(Controller):
    """
    Controller to test authentication, authorization, and sessions across multiple routes.
    """
    prefix = "/api/dashboard"

    @GET("/home")
    @authenticated
    async def home(self, ctx: RequestCtx):
        """
        Public-facing dashboard home (authenticated).
        """
        user = ctx.identity
        return Response.json({
            "message": f"Welcome to the dashboard, {user.get_attribute('username')}!",
            "user_id": user.id,
            "roles": user.get_attribute("roles", [])
        })

    @GET("/stats")
    async def stats(self, ctx: RequestCtx):
        """
        Stats page (manual auth check).
        """
        if not hasattr(ctx, "identity") or not ctx.identity:
            return Response.json({"error": "Auth required for stats"}, status=401)
            
        return Response.json({
            "status": "online",
            "active_users": 42,
            "your_id": ctx.identity.id
        })

    @GET("/settings")
    @authenticated
    async def settings(self, ctx: RequestCtx):
        """
        Admin-only settings.
        """
        user = ctx.identity
        roles = user.get_attribute("roles", [])
        if "admin" not in roles:
            return Response.json({
                "error": "Admin role required",
                "your_roles": roles,
                "user_id": user.id
            }, status=403)
            
        return Response.json({
            "settings": {
                "theme": "dark",
                "notifications": True,
                "admin_debug": True
            }
        })

    @POST("/pref")
    @stateful
    async def save_pref(self, ctx: RequestCtx, state: Any):
        """
        Save a preference to the session state.
        """
        sess = ctx.request.state.get("session")
        data = await ctx.json()
        pref = data.get("pref")
        value = data.get("value")
        
        if not pref:
            return Response.json({"error": "Missing pref"}, status=400)
            
        # SessionState is a wrapper around session.data
        state[pref] = value
        return Response.json({"status": "saved", "pref": pref, "value": value})

    @GET("/pref")
    @stateful
    async def get_pref(self, ctx: RequestCtx, state: Any):
        """
        Get a preference from the session state.
        """
        sess = ctx.request.state.get("session")
        pref = ctx.request.query_param("pref")
        if not pref:
            return Response.json({"prefs": state.to_dict()})
            
        return Response.json({pref: state.get(pref)})
