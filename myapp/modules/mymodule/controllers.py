"""
Mymodule module controllers (request handlers).

This file defines the HTTP endpoints for the mymodule module
using the modern Controller architecture with pattern-based routing.
"""

from aquilia import Controller, GET, POST, PUT, DELETE, RequestCtx, Response
from aquilia.sessions import Session, SessionPrincipal
from .faults import MymoduleNotFoundFault
from .services import MymoduleService


class MymoduleController(Controller):
    """
    Controller for mymodule endpoints.

    Provides RESTful CRUD operations for mymodule.
    """
    prefix = "/mymodule"
    tags = ["mymodule"]

    def __init__(self, service: MymoduleService):
        self.service = service

    @GET("/")
    async def list_mymodule(self, ctx: RequestCtx):
        """
        Get list of mymodule.

        Example:
            GET /mymodule/ -> {"items": [...], "total": 0}
        """
        items = await self.service.get_all()

        return Response.json({
            "items": items,
            "total": len(items)
        })

    @POST("/")
    async def create_mymodule(self, ctx: RequestCtx):
        """
        Create new mymodule.

        Example:
            POST /mymodule/
            Body: {"name": "Example"}
            -> {"id": 1, "name": "Example"}
        """
        data = await ctx.json()
        item = await self.service.create(data)
        return Response.json(item, status=201)

    @GET("/«id:int»")
    async def get_mymodule(self, ctx: RequestCtx, id: int):
        """
        Get single mymodule by ID.

        Example:
            GET /mymodule/1 -> {"id": 1, "name": "Example"}
        """
        item = await self.service.get_by_id(id)
        if not item:
            raise MymoduleNotFoundFault(item_id=id)

        return Response.json(item)

    @PUT("/«id:int»")
    async def update_mymodule(self, ctx: RequestCtx, id: int):
        """
        Update mymodule by ID.

        Example:
            PUT /mymodule/1
            Body: {"name": "Updated"}
            -> {"id": 1, "name": "Updated"}
        """
        data = await ctx.json()
        item = await self.service.update(id, data)
        if not item:
            raise MymoduleNotFoundFault(item_id=id)

        return Response.json(item)

    @DELETE("/«id:int»")
    async def delete_mymodule(self, ctx: RequestCtx, id: int):
        """
        Delete mymodule by ID.

        Example:
            DELETE /mymodule/1 -> 204 No Content
        """
        deleted = await self.service.delete(id)
        if not deleted:
            raise MymoduleNotFoundFault(item_id=id)

        return Response(status=204)

    # Session-aware endpoints
    @GET("/session")
    async def get_session_info(self, ctx: RequestCtx):
        """
        Get current session information.
        
        Example:
            GET /mymodule/session -> {
                "session_id": "sess_abc123...",
                "user_id": "user_sess_abc123...",
                "session_data": {...},
                "user_items_count": 0,
                "created_at": "2026-01-25T...",
                "is_authenticated": false
            }
        """
        session_info = await self.service.get_session_info(ctx.session)
        return Response.json(session_info)

    @POST("/session/login")
    async def login_user(self, ctx: RequestCtx):
        """
        Login user and create authenticated session.
        
        Example:
            POST /mymodule/session/login
            Body: {"username": "john", "role": "user"}
            -> {"message": "Logged in", "session_id": "sess_abc123...", "user_id": "john"}
        """
        data = await ctx.json()
        username = data.get("username", "anonymous")
        role = data.get("role", "user")
        
        # Ensure we have a session
        if ctx.session is None:
            # In a real implementation, session middleware should create this
            # For testing purposes, we'll handle the None case gracefully
            from datetime import datetime
            login_time = datetime.now().isoformat()
            authenticated_at = login_time
            session_id = "no-session"
        else:
            login_time = ctx.session.created_at.isoformat()
            authenticated_at = ctx.session.last_accessed_at.isoformat()
            session_id = str(ctx.session.id)
        
        # Create principal
        principal = SessionPrincipal(
            kind="user",
            id=username,
            attributes={
                "role": role,
                "login_time": login_time
            }
        )
        
        # Bind to session if available
        if ctx.session is not None:
            ctx.session.principal = principal
            ctx.session.data["user_id"] = username
            ctx.session.data["authenticated_at"] = authenticated_at
        
        return Response.json({
            "message": "Logged in successfully",
            "session_id": session_id,
            "user_id": username,
            "role": role
        })

    @POST("/session/logout")
    async def logout_user(self, ctx: RequestCtx):
        """
        Logout user and clear session data.
        
        Example:
            POST /mymodule/session/logout
            -> {"message": "Logged out", "session_id": "sess_abc123..."}
        """
        session_id = str(ctx.session.id) if ctx.session else "no-session"
        
        # Clear authentication data if session exists
        if ctx.session is not None:
            ctx.session.principal = None
            ctx.session.data.pop("user_id", None)
            ctx.session.data.pop("authenticated_at", None)
        
        return Response.json({
            "message": "Logged out successfully",
            "session_id": session_id
        })

    @GET("/my-items")
    async def get_my_items(self, ctx: RequestCtx):
        """
        Get items for the current user session.
        
        Example:
            GET /mymodule/my-items -> {"items": [...], "total": 0}
        """
        items = await self.service.get_user_items(ctx.session)
        return Response.json({
            "items": items,
            "total": len(items),
            "user_id": ctx.session.data.get("user_id"),
            "session_id": str(ctx.session.id)
        })

    @POST("/my-items")
    async def create_my_item(self, ctx: RequestCtx):
        """
        Create item for the current user session.
        
        Example:
            POST /mymodule/my-items
            Body: {"name": "My Item", "description": "Personal item"}
            -> {"id": 1, "user_id": "user_sess_abc123...", "name": "My Item", ...}
        """
        data = await ctx.json()
        item = await self.service.create_user_item(ctx.session, data)
        return Response.json(item, status=201)