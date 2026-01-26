"""
Comprehensive Authentication System for Aquilia Demo

Features:
- Login/Logout with sessions and templates
- Bearer token authentication
- Role-based access control
- Password hashing with verification
- Template-based login page
- Dashboard with session info
- Demo users (admin/password, john/password)
"""

from typing import Optional
from datetime import datetime, timezone
from pathlib import Path
from aquilia import Controller, GET, POST, RequestCtx, Response
from aquilia.di import service, inject
from aquilia.auth.manager import AuthManager
from aquilia.auth.stores import MemoryIdentityStore, MemoryCredentialStore
from aquilia.auth.core import Identity, IdentityStatus, IdentityType, PasswordCredential, CredentialStatus
from aquilia.auth.hashing import PasswordHasher
import uuid
import logging

logger = logging.getLogger(__name__)


@service(scope="app")
class DemoAuthService:
    """Authentication service with pre-populated demo users."""
    
    def __init__(
        self,
        identity_store: MemoryIdentityStore,
        credential_store: MemoryCredentialStore,
        password_hasher: PasswordHasher,
    ):
        self.identity_store = identity_store
        self.credential_store = credential_store
        self.password_hasher = password_hasher
        self._initialized = False
    
    async def ensure_demo_users(self):
        """Initialize demo users if not already done."""
        if self._initialized:
            return
        
        # Admin user
        admin_id = "admin-001"
        admin = Identity(
            id=admin_id,
            type=IdentityType.USER,
            attributes={
                "username": "admin",
                "email": "admin@example.com",
                "roles": {"admin", "user"},
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            status=IdentityStatus.ACTIVE,
        )
        
        try:
            await self.identity_store.create(admin)
            admin_pass = self.password_hasher.hash("password")
            admin_cred = PasswordCredential(
                identity_id=admin_id,
                password_hash=admin_pass,
                status=CredentialStatus.ACTIVE,
                created_at=datetime.now(timezone.utc),
                last_changed_at=datetime.now(timezone.utc),
            )
            await self.credential_store.save_password(admin_cred)
        except Exception as e:
            logger.debug(f"Admin user already exists: {e}")
        
        # Regular user
        user_id = "user-001"
        user = Identity(
            id=user_id,
            type=IdentityType.USER,
            attributes={
                "username": "john",
                "email": "john@example.com",
                "roles": {"user"},
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            status=IdentityStatus.ACTIVE,
        )
        
        try:
            await self.identity_store.create(user)
            user_pass = self.password_hasher.hash("password")
            user_cred = PasswordCredential(
                identity_id=user_id,
                password_hash=user_pass,
                status=CredentialStatus.ACTIVE,
                created_at=datetime.now(timezone.utc),
                last_changed_at=datetime.now(timezone.utc),
            )
            await self.credential_store.save_password(user_cred)
        except Exception as e:
            logger.debug(f"User already exists: {e}")
        
        self._initialized = True
    
    async def verify_credentials(self, username: str, password: str) -> Optional[Identity]:
        """Verify username/password and return Identity if valid."""
        await self.ensure_demo_users()
        
        # Find user by username using get_by_attribute
        identity = await self.identity_store.get_by_attribute("username", username)
        
        if not identity:
            return None
        
        # Verify password
        try:
            cred = await self.credential_store.get_password(identity.id)
            if cred and self.password_hasher.verify(cred.password_hash, password):
                return identity
        except Exception as e:
            logger.debug(f"Password verification failed: {e}")
        
        return None


@service(scope="app")
class UserService:
    """
    Service for managing user accounts.
    """
    def __init__(
        self,
        identity_store: MemoryIdentityStore,
        credential_store: MemoryCredentialStore,
        password_hasher: PasswordHasher
    ):
        self.identity_store = identity_store
        self.credential_store = credential_store
        self.password_hasher = password_hasher

    async def register_user(self, username: str, password: str, email: Optional[str] = None, roles: list[str] = None) -> Identity:
        """Register a new user."""
        # 1. Create Identity
        user_id = str(uuid.uuid4())
        identity = Identity(
            id=user_id,
            type=IdentityType.USER,
            attributes={
                "username": username,
                "email": email,
                "provider": "local",
                "roles": roles or ["user"]
            },
            status=IdentityStatus.ACTIVE,
        )
        
        await self.identity_store.create(identity)
        
        # 2. Create Credential
        hashed = self.password_hasher.hash(password)
        credential = PasswordCredential(
            identity_id=user_id,
            password_hash=hashed
        )
        
        await self.credential_store.save_password(credential)
        
        logger.info(f"Registered user: {username} ({user_id})")
        return identity


class AuthController(Controller):
    """
    Controller for authentication with template-based UI.
    """
    prefix = "/auth"
    tags = ["auth"]

    def __init__(self, auth_manager: AuthManager, user_service: UserService, demo_service: DemoAuthService):
        self.auth_manager = auth_manager
        self.user_service = user_service
        self.demo_service = demo_service

    @GET("/login")
    async def login_page(self, ctx: RequestCtx):
        """Display login page template."""
        from aquilia.templates import TemplateEngine
        from aquilia.templates.loader import TemplateLoader
        
        search_paths = [Path("myapp/modules/myappmod/templates")]
        loader = TemplateLoader(search_paths=search_paths)
        engine = TemplateEngine(loader=loader)
        
        return self.render("login.html", {}, ctx, engine=engine)
    
    @POST("/login")
    async def login_submit(self, ctx: RequestCtx):
        """Handle login form submission."""
        from aquilia.templates import TemplateEngine
        from aquilia.templates.loader import TemplateLoader
        
        # Parse form data
        body = await ctx.request.get_body()
        params = {}
        if body:
            for pair in body.split("&"):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    params[k] = v
        
        username = params.get("username", "")
        password = params.get("password", "")
        
        # Verify credentials
        identity = await self.demo_service.verify_credentials(username, password)
        
        if not identity:
            # Re-render login with error
            search_paths = [Path("myapp/modules/myappmod/templates")]
            loader = TemplateLoader(search_paths=search_paths)
            engine = TemplateEngine(loader=loader)
            
            # Add flash message via session
            if ctx.session:
                ctx.session.data["_flash_messages"] = [
                    {"text": "Invalid username or password", "level": "danger"}
                ]
            
            return self.render("login.html", {}, ctx, engine=engine, status=401)
        
        # Set identity on session and context
        if ctx.session:
            ctx.session.principal = identity
            ctx.session.data["user_id"] = identity.id
        ctx.identity = identity
        
        # Add success flash message
        if ctx.session:
            ctx.session.data["_flash_messages"] = [
                {"text": f"Welcome back, {identity.get_attribute('username')}!", "level": "success"}
            ]
        
        # Redirect to dashboard
        return Response.redirect("/dashboard")
    
    @GET("/logout")
    async def logout(self, ctx: RequestCtx):
        """Handle logout."""
        # Clear session
        if ctx.session:
            ctx.session.data.clear()
            ctx.session.principal = None
        
        ctx.identity = None
        
        # Redirect to login
        return Response.redirect("/login")

    @POST("/login-json")
    async def login_json(self, ctx: RequestCtx):
        """
        Login with username and password (JSON API).
        """
        data = await ctx.json()
        username = data.get("username")
        password = data.get("password")
        
        if not username or not password:
            return Response.json({"error": "Missing credentials"}, status=400)
            
        try:
            result = await self.auth_manager.authenticate_password(username, password)
            return Response.json({
                "access_token": result.access_token,
                "refresh_token": result.refresh_token,
                "token_type": "Bearer",
                "expires_in": result.expires_in
            })
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return Response.json({"error": str(e)}, status=401)

    @GET("/me")
    async def me(self, ctx: RequestCtx):
        """
        Get current user identity.
        """
        if not hasattr(ctx, "identity") or not ctx.identity:
            return Response.json({"error": "Not authenticated"}, status=401)
            
        return Response.json({
            "id": ctx.identity.id,
            "username": ctx.identity.get_attribute("username"),
            "email": ctx.identity.get_attribute("email"),
            "roles": ctx.identity.get_attribute("roles", [])
        })

    @POST("/register")
    async def register(self, ctx: RequestCtx):
        """
        Register a new user.
        """
        data = await ctx.json()
        username = data.get("username")
        password = data.get("password")
        email = data.get("email")
        roles = data.get("roles", ["user"])
        
        if not username or not password:
            return Response.json({"error": "Missing username or password"}, status=400)
            
        try:
            identity = await self.user_service.register_user(username, password, email, roles)
            resp_roles = identity.get_attribute("roles")
            return Response.json({
                "id": identity.id,
                "username": identity.get_attribute("username"),
                "email": identity.get_attribute("email"),
                "roles": resp_roles
            }, status=201)
        except Exception as e:
            logger.error(f"Registration failed: {e}")
            return Response.json({"error": str(e)}, status=400)


class DashboardController(Controller):
    """Dashboard and main pages."""
    
    prefix = ""
    
    @GET("/dashboard")
    async def dashboard(self, ctx: RequestCtx):
        """Display dashboard."""
        from aquilia.templates import TemplateEngine
        from aquilia.templates.loader import TemplateLoader
        
        search_paths = [Path("myapp/modules/myappmod/templates")]
        loader = TemplateLoader(search_paths=search_paths)
        engine = TemplateEngine(loader=loader)
        
        return self.render("dashboard.html", {}, ctx, engine=engine)
    
    @GET("/profile")
    async def profile(self, ctx: RequestCtx):
        """Display user profile."""
        from aquilia.templates import TemplateEngine
        from aquilia.templates.loader import TemplateLoader
        
        search_paths = [Path("myapp/modules/myappmod/templates")]
        loader = TemplateLoader(search_paths=search_paths)
        engine = TemplateEngine(loader=loader)
        
        return self.render("profile.html", {}, ctx, engine=engine)
    
    @GET("/")
    async def home(self, ctx: RequestCtx):
        """Home page - redirect to dashboard."""
        return Response.redirect("/dashboard")


class SessionsController(Controller):
    """Session management pages."""
    
    prefix = "/sessions"
    
    @GET("/list")
    async def list_sessions(self, ctx: RequestCtx):
        """Display active sessions."""
        from aquilia.templates import TemplateEngine
        from aquilia.templates.loader import TemplateLoader
        
        # Prepare sessions data for template
        sessions_data = []
        if ctx.session:
            sessions_data.append({
                "id": str(ctx.session.id),
                "created_at": ctx.session.created_at.isoformat() if ctx.session.created_at else "N/A",
                "expires_at": ctx.session.expires_at.isoformat() if ctx.session.expires_at else "Never",
                "authenticated": bool(ctx.session.principal),
                "data_size": len(str(ctx.session.data).encode()),
            })
        
        search_paths = [Path("myapp/modules/myappmod/templates")]
        loader = TemplateLoader(search_paths=search_paths)
        engine = TemplateEngine(loader=loader)
        
        return self.render(
            "sessions.html",
            {"sessions": sessions_data},
            ctx,
            engine=engine
        )


__all__ = ["AuthController", "DashboardController", "SessionsController", "DemoAuthService", "UserService"]
