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

    def __init__(self):
        # Instantiate service directly (DI integration pending)
        # Once DI is fully integrated, change to: def __init__(self, service: MyappmodService):
        self.service = MyappmodService()

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