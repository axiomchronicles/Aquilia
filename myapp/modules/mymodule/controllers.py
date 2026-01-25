"""
Mymodule module controllers (request handlers).

This file defines the HTTP endpoints for the mymodule module
using the modern Controller architecture with pattern-based routing.
"""

from aquilia import Controller, GET, POST, PUT, DELETE, RequestCtx, Response
from aquilia.sessions import Session, SessionPrincipal, session
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

    @GET("/<<id:int>>")
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
    @session.ensure()
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
    @session.ensure()
    async def login_user(self, ctx: RequestCtx, session: Session):
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
        
        # Use injected session directly
        login_time = session.created_at.isoformat()
        authenticated_at = session.last_accessed_at.isoformat()
        session_id = str(session.id)
        
        # Create principal
        principal = SessionPrincipal(
            kind="user",
            id=username,
            attributes={
                "role": role,
                "login_time": login_time
            }
        )
        
        # Bind to session
        session.mark_authenticated(principal)
        session.data["user_id"] = username
        session.data["authenticated_at"] = authenticated_at
        
        return Response.json({
            "message": "Logged in successfully",
            "session_id": session_id,
            "user_id": username,
            "role": role
        })
    @POST("/session/logout")
    @session.ensure()
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
    @session.ensure()
    async def get_my_items(self, ctx: RequestCtx):
        """
        Get items for the current user session.
        
        Example:
            GET /mymodule/my-items -> {"items": [...], "total": 0}
        """
        items = await self.service.get_user_items(ctx.session)
        user_id = ctx.session.data.get("user_id") if ctx.session else None
        session_id = str(ctx.session.id) if ctx.session else "no-session"
        
        return Response.json({
            "items": items,
            "total": len(items),
            "user_id": user_id,
            "session_id": session_id
        })

    @POST("/my-items")
    @session.ensure()
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

    @PUT("/my-items/«id:int»")
    @session.ensure()
    async def update_my_item(self, ctx: RequestCtx, id: int):
        """Update a specific item for the current user session."""
        data = await ctx.json()
        item = await self.service.update_user_item(ctx.session, id, data)
        if not item:
            raise MymoduleNotFoundFault(f"Item {id} not found")
        return Response.json(item)

    @DELETE("/my-items/«id:int»")
    @session.ensure()
    async def delete_my_item(self, ctx: RequestCtx, id: int):
        """Delete a specific item for the current user session."""
        deleted = await self.service.delete_user_item(ctx.session, id)
        if not deleted:
            raise MymoduleNotFoundFault(f"Item {id} not found")
        return Response(status=204)