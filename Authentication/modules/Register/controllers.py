"""
Register module controllers (request handlers).

This file defines the HTTP endpoints for the Register module
using the modern Controller architecture with pattern-based routing.
"""

from aquilia import Controller, GET, POST, PUT, DELETE, RequestCtx, Response
from .faults import RegisterNotFoundFault
from .services import RegisterService


class RegisterController(Controller):
    """
    Controller for Register endpoints.

    Provides RESTful CRUD operations for Register.
    """
    prefix = "/"
    tags = ["Register"]

    def __init__(self, service: "RegisterService" = None):
        # Instantiate service directly if not injected
        self.service = service or RegisterService()

    @GET("/")
    async def list_Register(self, ctx: RequestCtx):
        """
        List all Register.

        Example:
            GET /Register/ -> {"items": [...], "total": 0}
        """
        items = await self.service.get_all()

        return Response.json({
            "items": items,
            "total": len(items)
        })

    @POST("/")
    async def create_Register(self, ctx: RequestCtx):
        """
        Create a new Register.

        Example:
            POST /Register/
            Body: {"name": "Example"}
            -> {"id": 1, "name": "Example"}
        """
        data = await ctx.json()
        item = await self.service.create(data)
        return Response.json(item, status=201)

    @GET("/«id:int»")
    async def get_Register(self, ctx: RequestCtx, id: int):
        """
        Get a Register by ID.

        Example:
            GET /Register/1 -> {"id": 1, "name": "Example"}
        """
        item = await self.service.get_by_id(id)
        if not item:
            raise RegisterNotFoundFault(item_id=id)

        return Response.json(item)

    @PUT("/«id:int»")
    async def update_Register(self, ctx: RequestCtx, id: int):
        """
        Update a Register by ID.

        Example:
            PUT /Register/1
            Body: {"name": "Updated"}
            -> {"id": 1, "name": "Updated"}
        """
        data = await ctx.json()
        item = await self.service.update(id, data)
        if not item:
            raise RegisterNotFoundFault(item_id=id)

        return Response.json(item)

    @DELETE("/«id:int»")
    async def delete_Register(self, ctx: RequestCtx, id: int):
        """
        Delete a Register by ID.

        Example:
            DELETE /Register/1 -> 204 No Content
        """
        deleted = await self.service.delete(id)
        if not deleted:
            raise RegisterNotFoundFault(item_id=id)

        return Response(status=204)