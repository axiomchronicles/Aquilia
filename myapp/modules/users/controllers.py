"""
Users Module — Controllers

Full REST API for user management and authentication.

Integrates:
- Aquilia Controller (class-based with prefix/tags/pipeline)
- Aquilia Route Decorators (@GET, @POST, @PUT, @DELETE, @PATCH)
- Aquilia RequestCtx (request, identity, session, container, state)
- Aquilia Response (JSON, SSE, streaming, cookies, caching)
- Aquilia Serializers (request validation, response shaping)
- Aquilia Sessions (session state for auth flow)
- Aquilia Auth (identity, authenticated endpoints)
- Aquilia Faults (structured error responses)
"""

from aquilia.controller import Controller
from aquilia.controller.decorators import GET, POST, PUT, DELETE, PATCH
from aquilia.engine import RequestCtx
from aquilia.response import Response

from .services import UserService, AuthService
from .serializers import (
    LoginSerializer,
    RegisterSerializer,
    PasswordChangeSerializer,
    UserPublicSerializer,
    UserDetailSerializer,
    UserUpdateSerializer,
    UserAdminSerializer,
    UserAddressSerializer,
    UserSessionSerializer,
    AuthTokenSerializer,
)
from .faults import InsufficientPermissionsFault


class AuthController(Controller):
    """
    Authentication endpoints — login, register, logout, token refresh.

    Uses Aquilia Sessions for session-based auth + token issuance.
    """
    prefix = "/auth"
    tags = ["Authentication"]

    def __init__(self, auth_service: AuthService = None):
        self.auth = auth_service

    @POST("/register")
    async def register(self, ctx: RequestCtx) -> Response:
        """Register a new user account."""
        serializer = await RegisterSerializer.from_request_async(ctx.request)
        serializer.is_valid(raise_fault=True)

        from .services import UserService
        user_service = await ctx.container.resolve_async(UserService)
        user = await user_service.create_user(serializer.validated_data)

        result = UserPublicSerializer(instance=user)
        return Response.json(result.data, status=201)

    @POST("/login")
    async def login(self, ctx: RequestCtx) -> Response:
        """Authenticate and receive tokens + session."""
        serializer = await LoginSerializer.from_request_async(ctx.request)
        serializer.is_valid(raise_fault=True)

        auth_service = await ctx.container.resolve_async(AuthService)
        result = await auth_service.authenticate(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )

        # record session for audit (best-effort)
        try:
            await auth_service.record_session(
                user=result["user"],
                session_id=str(ctx.session.id) if ctx.session else "api",
                ip_address=ctx.request.client_ip() or "unknown",
                user_agent=ctx.request.headers.get("user-agent", ""),
            )
        except Exception:
            pass  # session audit is non-critical

        token_data = AuthTokenSerializer(instance=result)
        return Response.json(token_data.data)

    @POST("/logout")
    async def logout(self, ctx: RequestCtx) -> Response:
        """Invalidate session and blacklist token."""
        auth_service = await ctx.container.resolve_async(AuthService)

        # blacklist token if present
        auth_header = ctx.request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]
            await auth_service.logout(token)

        # clear session
        if ctx.session:
            user_id = ctx.session.get("user_id")
            if user_id:
                await auth_service.revoke_session(
                    user_id, str(ctx.session.id)
                )
            ctx.session.clear_data()

        return Response.json({"message": "Logged out successfully"})

    @POST("/password/change")
    async def change_password(self, ctx: RequestCtx) -> Response:
        """Change password for the authenticated user."""
        if not ctx.identity:
            return Response.json({"error": "Unauthorized"}, status=401)

        serializer = await PasswordChangeSerializer.from_request_async(ctx.request)
        serializer.is_valid(raise_fault=True)

        user_service = await ctx.container.resolve_async(UserService)
        await user_service.update_password(
            user_id=int(ctx.identity.id),
            current_pw=serializer.validated_data["current_password"],
            new_pw=serializer.validated_data["new_password"],
        )

        return Response.json({"message": "Password changed successfully"})


class UserController(Controller):
    """
    User profile and management endpoints.

    Supports:
    - Self-service profile (GET/PUT /me)
    - Address management (CRUD under /me/addresses)
    - Session management (/me/sessions)
    - Admin user listing and management
    """
    prefix = "/users"
    tags = ["Users"]

    def __init__(self, user_service: UserService = None):
        self.users = user_service

    # ── Self-Service ─────────────────────────────────────────

    @GET("/me")
    async def get_profile(self, ctx: RequestCtx) -> Response:
        """Get the authenticated user's profile."""
        if not ctx.identity:
            return Response.json({"error": "Unauthorized"}, status=401)

        user_service = await ctx.container.resolve_async(UserService)
        user = await user_service.get_by_id(int(ctx.identity.id))
        serializer = UserDetailSerializer(instance=user)
        return Response.json(serializer.data)

    @PUT("/me")
    async def update_profile(self, ctx: RequestCtx) -> Response:
        """Update the authenticated user's profile."""
        if not ctx.identity:
            return Response.json({"error": "Unauthorized"}, status=401)

        serializer = await UserUpdateSerializer.from_request_async(ctx.request, partial=True)
        serializer.is_valid(raise_fault=True)

        user_service = await ctx.container.resolve_async(UserService)
        user = await user_service.update_user(
            int(ctx.identity.id), serializer.validated_data
        )
        result = UserDetailSerializer(instance=user)
        return Response.json(result.data)

    # ── Address Management ───────────────────────────────────

    @GET("/me/addresses")
    async def list_addresses(self, ctx: RequestCtx) -> Response:
        if not ctx.identity:
            return Response.json({"error": "Unauthorized"}, status=401)

        user_service = await ctx.container.resolve_async(UserService)
        addresses = await user_service.list_addresses(int(ctx.identity.id))
        serializer = UserAddressSerializer.many(instance=addresses)
        return Response.json(serializer.data)

    @POST("/me/addresses")
    async def add_address(self, ctx: RequestCtx) -> Response:
        if not ctx.identity:
            return Response.json({"error": "Unauthorized"}, status=401)

        serializer = await UserAddressSerializer.from_request_async(ctx.request)
        serializer.is_valid(raise_fault=True)

        user_service = await ctx.container.resolve_async(UserService)
        address = await user_service.add_address(
            int(ctx.identity.id), serializer.validated_data
        )
        result = UserAddressSerializer(instance=address)
        return Response.json(result.data, status=201)

    @DELETE("/me/addresses/«address_id:int»")
    async def delete_address(self, ctx: RequestCtx, address_id: int) -> Response:
        if not ctx.identity:
            return Response.json({"error": "Unauthorized"}, status=401)

        user_service = await ctx.container.resolve_async(UserService)
        await user_service.delete_address(int(ctx.identity.id), address_id)
        return Response.json({"message": "Address deleted"})

    # ── Session Management ───────────────────────────────────

    @GET("/me/sessions")
    async def list_sessions(self, ctx: RequestCtx) -> Response:
        if not ctx.identity:
            return Response.json({"error": "Unauthorized"}, status=401)

        auth_service = await ctx.container.resolve_async(AuthService)
        sessions = await auth_service.get_active_sessions(int(ctx.identity.id))
        serializer = UserSessionSerializer.many(instance=sessions)
        return Response.json(serializer.data)

    @DELETE("/me/sessions/«session_id»")
    async def revoke_session(self, ctx: RequestCtx, session_id: str) -> Response:
        if not ctx.identity:
            return Response.json({"error": "Unauthorized"}, status=401)

        auth_service = await ctx.container.resolve_async(AuthService)
        await auth_service.revoke_session(int(ctx.identity.id), session_id)
        return Response.json({"message": "Session revoked"})

    # ── Admin Endpoints ──────────────────────────────────────

    @GET("/")
    async def list_users(self, ctx: RequestCtx) -> Response:
        """Admin: list all users with filtering and pagination."""
        if not ctx.identity or "admin" not in (ctx.identity.attributes.get("roles", []) or []):
            raise InsufficientPermissionsFault("admin")

        params = ctx.request.query_params
        user_service = await ctx.container.resolve_async(UserService)
        result = await user_service.list_users(
            page=int(params.get("page", 1)),
            page_size=int(params.get("page_size", 20)),
            role=params.get("role"),
            is_active=params.get("is_active") == "true" if "is_active" in params else None,
            search=params.get("search"),
        )

        serializer = UserPublicSerializer.many(instance=result["items"])
        return Response.json({
            "items": serializer.data,
            "total": result["total"],
            "page": result["page"],
            "page_size": result["page_size"],
            "pages": result["pages"],
        })

    @GET("/«user_id:int»")
    async def get_user(self, ctx: RequestCtx, user_id: int) -> Response:
        """Admin: get user detail."""
        if not ctx.identity or "admin" not in (ctx.identity.attributes.get("roles", []) or []):
            raise InsufficientPermissionsFault("admin")

        user_service = await ctx.container.resolve_async(UserService)
        user = await user_service.get_by_id(user_id)
        serializer = UserAdminSerializer(instance=user)
        return Response.json(serializer.data)

    @PATCH("/«user_id:int»/role")
    async def change_role(self, ctx: RequestCtx, user_id: int) -> Response:
        """Admin: change a user's role."""
        if not ctx.identity:
            raise InsufficientPermissionsFault("superadmin")

        body = await ctx.request.json()
        user_service = await ctx.container.resolve_async(UserService)
        user = await user_service.change_role(
            user_id,
            new_role=body.get("role", ""),
            actor_role=ctx.identity.attributes.get("roles", [])[0] if ctx.identity.attributes.get("roles", []) else "",
        )
        serializer = UserAdminSerializer(instance=user)
        return Response.json(serializer.data)

    @DELETE("/«user_id:int»")
    async def deactivate_user(self, ctx: RequestCtx, user_id: int) -> Response:
        """Admin: deactivate a user."""
        if not ctx.identity or "admin" not in (ctx.identity.attributes.get("roles", []) or []):
            raise InsufficientPermissionsFault("admin")

        user_service = await ctx.container.resolve_async(UserService)
        user = await user_service.deactivate_user(user_id)
        return Response.json({"message": f"User {user.username} deactivated"})
