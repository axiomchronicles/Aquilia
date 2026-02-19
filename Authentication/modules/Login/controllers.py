"""
Login module controllers (request handlers).

This file defines the HTTP endpoints for the Login module
using the modern Controller architecture with pattern-based routing.
"""

from aquilia import Controller, GET, POST, PUT, DELETE, RequestCtx, Response
from .faults import LoginNotFoundFault
from .services import LoginService
from aquilia.templates import TemplateEngine

from .serilizers import UserSerilizer


class LoginController(Controller):
    """
    Controller for Login endpoints.

    Provides RESTful CRUD operations for Login.
    """
    prefix = "/"
    tags = ["Login"]

    def __init__(self,
            userserilizer: "UserSerilizer" = UserSerilizer,
            # template = TemplateEngine
            # template = TemplateEngine
    ):
        # Instantiate service directly if not injected
        # self.template = template
        # self._template_engine = TemplateEngine
        ...

    @GET("/")
    async def test_login(self, ctx: RequestCtx):
        return await self.render("login.html")