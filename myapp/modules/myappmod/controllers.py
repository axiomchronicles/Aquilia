"""
Myappmod module controllers (request handlers).

This file defines the HTTP endpoints for the myappmod module
using the modern Controller architecture with pattern-based routing.
"""

from aquilia import Controller, GET, POST, PUT, DELETE, RequestCtx, Response
from .faults import MyappmodNotFoundFault
from .services import MyappmodService


class MyappmodController(Controller):
    """
    Controller for myappmod endpoints.

    Provides RESTful CRUD operations for myappmod.
    """
    prefix = "/"
    tags = ["myappmod"]

    def __init__(self, service: MyappmodService):
        # Instantiate service directly if not injected
        self.service = service

    @GET("/")
    async def list_myappmod(self, ctx: RequestCtx):
        """
        Get list of myappmod.

        Example:
            GET /myappmod/ -> {"items": [...], "total": 0}
        """
        items = await self.service.get_all()

        return Response.json({
            "items": items,
            "total": len(items)
        })

    @POST("/")
    async def create_myappmod(self, ctx: RequestCtx):
        """
        Create new myappmod.

        Example:
            POST /myappmod/
            Body: {"name": "Example"}
            -> {"id": 1, "name": "Example"}
        """
        data = await ctx.json()
        item = await self.service.create(data)
        return Response.json(item, status=201)

    @GET("/«id:int»")
    async def get_myappmod(self, ctx: RequestCtx, id: int):
        """
        Get single myappmod by ID.

        Example:
            GET /myappmod/1 -> {"id": 1, "name": "Example"}
        """
        item = await self.service.get_by_id(id)
        if not item:
            raise MyappmodNotFoundFault(item_id=id)

        return Response.json(item)

    @PUT("/«id:int»")
    async def update_myappmod(self, ctx: RequestCtx, id: int):
        """
        Update myappmod by ID.

        Example:
            PUT /myappmod/1
            Body: {"name": "Updated"}
            -> {"id": 1, "name": "Updated"}
        """
        data = await ctx.json()
        item = await self.service.update(id, data)
        if not item:
            raise MyappmodNotFoundFault(item_id=id)

        return Response.json(item)

    @DELETE("/«id:int»")
    async def delete_myappmod(self, ctx: RequestCtx, id: int):
        """
        Delete myappmod by ID.

        Example:
            DELETE /myappmod/1 -> 204 No Content
        """
        deleted = await self.service.delete(id)
        if not deleted:
            raise MyappmodNotFoundFault(item_id=id)

        return Response(status=204)
from .services_ext import AuditLogger, LazyProcessor

class AdvancedFeaturesController(Controller):
    """
    Demonstrates advanced DI features like Request Scoping and Lazy Proxies.
    """
    prefix = "/advanced"
    tags = ["advanced"]
    
    def __init__(self, auditor: AuditLogger, processor: LazyProcessor):
        # AuditLogger is request-scoped (depends on UserIdentity)
        # LazyProcessor simulates lazy loading
        self.auditor = auditor
        self.processor = processor
        
    @GET("/audit")
    async def audit_check(self, ctx):
        """
        Demonstrates request-scoped injection.
        The UserIdentity was injected into AuditLogger by the middleware.
        """
        # Log an action
        log = self.auditor.log_action("Accessed Audit Endpoint")
        return {"log_entry": log}
        
    @GET("/lazy/«data:str»")
    async def lazy_check(self, ctx, data: str):
        """
        Demonstrates lazy injection.
        ExpensiveService is only created now, when self.processor.process() calls it.
        """
        result = await self.processor.process(data)
        return {"result": result}
