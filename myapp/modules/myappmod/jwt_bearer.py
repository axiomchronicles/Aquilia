from aquilia.controller import Controller, GET, RequestCtx
from aquilia.response import Response
from aquilia.sessions.decorators import authenticated
from aquilia.auth.core import Identity
from typing import Any

class JwtBearerController(Controller):
    """
    Controller to specifically test and demonstrate JWT Bearer authentication.
    """
    prefix = "/jwt"

    @GET("/protected")
    @authenticated
    async def protected(self, ctx: RequestCtx):
        """
        A route protected by @authenticated.
        When called with 'Authorization: Bearer <token>', 
        AquilAuthMiddleware resolves the identity from the JWT.
        """
        user = ctx.identity
        return Response.json({
            "message": "Access granted via JWT Bearer token!",
            "user_id": user.id,
            "username": user.get_attribute("username")
        })

    @GET("/info")
    @authenticated
    async def info(self, ctx: RequestCtx):
        """
        Returns detailed info about the authenticated identity.
        """
        user = ctx.identity
        return Response.json({
            "identity": user.to_dict(),
            "roles": user.get_attribute("roles", []),
            "scopes": user.get_attribute("scopes", [])
        })
