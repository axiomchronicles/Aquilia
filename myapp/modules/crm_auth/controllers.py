"""
CRM Auth Controllers — Page routes + API routes.
Uses Aquilia Controller, Guards, Sessions, Templates, and Effects.
"""

from aquilia import Controller, GET, POST, RequestCtx, Response
from aquilia.templates import TemplateEngine
from aquilia.effects import DBTx

from modules.shared.serializers import RegisterSerializer, LoginSerializer
from modules.shared.faults import UnauthorizedFault
from .services import CRMAuthService


class AuthPageController(Controller):
    """
    Template-rendered auth pages: login, register, profile.
    Uses Aquilia TemplateEngine for server-side rendering.
    """

    prefix = "/"
    tags = ["auth", "pages"]

    def __init__(self, templates: TemplateEngine = None, auth_service: CRMAuthService = None):
        self.templates = templates
        self.auth_service = auth_service

    @GET("/login")
    async def login_page(self, ctx: RequestCtx):
        """Render login page."""
        return await self.templates.render_to_response(
            "auth/login.html",
            {"page_title": "Login — CRM"},
            request_ctx=ctx,
        )

    @GET("/register")
    async def register_page(self, ctx: RequestCtx):
        """Render registration page."""
        return await self.templates.render_to_response(
            "auth/register.html",
            {"page_title": "Register — CRM"},
            request_ctx=ctx,
        )

    @GET("/profile")
    async def profile_page(self, ctx: RequestCtx):
        """Render user profile page (requires auth via session)."""
        user = ctx.state.get("user")
        if not user:
            return Response.redirect("/auth/login")
        return await self.templates.render_to_response(
            "auth/profile.html",
            {"page_title": "Profile — CRM", "user": user},
            request_ctx=ctx,
        )


class AuthAPIController(Controller):
    """
    JSON API endpoints for authentication.
    Uses serializers for validation and effects for DB transactions.
    """

    prefix = "/api"
    tags = ["auth", "api"]

    def __init__(self, auth_service: CRMAuthService = None):
        self.auth_service = auth_service

    @POST("/register", status_code=201)
    async def api_register(self, ctx: RequestCtx):
        """Register a new user via API."""
        data = await ctx.json()
        serializer = RegisterSerializer(data=data)
        if not serializer.is_valid():
            return Response.json(
                {"error": "Validation failed", "details": serializer.errors},
                status=400,
            )
        user = await self.auth_service.register(serializer.validated_data)
        return Response.json({"user": user, "message": "Registration successful"}, status=201)

    @POST("/login")
    async def api_login(self, ctx: RequestCtx):
        """Login and receive JWT tokens."""
        data = await ctx.json()
        serializer = LoginSerializer(data=data)
        if not serializer.is_valid():
            return Response.json(
                {"error": "Validation failed", "details": serializer.errors},
                status=400,
            )
        result = await self.auth_service.login(
            serializer.validated_data["email"],
            serializer.validated_data["password"],
        )

        # Set session cookie
        if ctx.session:
            from aquilia.sessions import SessionPrincipal
            ctx.session.mark_authenticated(
                SessionPrincipal("user", str(result["user"]["id"]))
            )
            ctx.session.data["user_id"] = result["user"]["id"]
            ctx.session.data["user_email"] = result["user"]["email"]
            ctx.session.data["user_role"] = result["user"]["role"]
            ctx.session.data["user_name"] = result["user"].get("full_name", "")

        response = Response.json({
            "user": result["user"],
            "tokens": result["tokens"],
            "message": "Login successful",
        })

        # Set auth token cookie for template pages
        if result["tokens"].get("access_token"):
            response.set_cookie(
                "crm_token",
                result["tokens"]["access_token"],
                httponly=True,
                samesite="lax",
                max_age=3600,
            )

        return response

    @POST("/logout")
    async def api_logout(self, ctx: RequestCtx):
        """Logout — clear session and tokens."""
        if ctx.session:
            ctx.session.data.clear()

        response = Response.json({"message": "Logged out"})
        response.delete_cookie("crm_token")
        return response

    @GET("/me")
    async def api_me(self, ctx: RequestCtx):
        """Get current authenticated user."""
        user_id = None
        if ctx.session:
            user_id = ctx.session.data.get("user_id")

        if not user_id:
            return Response.json({"error": "Not authenticated"}, status=401)

        user = await self.auth_service.get_user_by_id(user_id)
        if not user:
            return Response.json({"error": "User not found"}, status=404)

        return Response.json({"user": user})

    @GET("/users")
    async def api_list_users(self, ctx: RequestCtx):
        """List all CRM users (admin/manager only)."""
        users = await self.auth_service.get_all_users()
        return Response.json({"users": users, "total": len(users)})
