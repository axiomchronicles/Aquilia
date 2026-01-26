
from typing import Optional
from aquilia import Controller, GET, POST, RequestCtx, Response
from aquilia.di import service, inject
from aquilia.auth.manager import AuthManager
from aquilia.auth.stores import MemoryIdentityStore, MemoryCredentialStore
from aquilia.auth.core import Identity, IdentityStatus, IdentityType, PasswordCredential
from aquilia.auth.hashing import PasswordHasher
from aquilia.auth.authz import RBACEngine
from aquilia.auth.mfa import MFAManager, TOTPProvider
import uuid
import logging

logger = logging.getLogger(__name__)

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
    Controller for authentication.
    """
    prefix = "/auth"
    tags = ["auth"]

    def __init__(self, auth_manager: AuthManager, user_service: UserService):
        self.auth_manager = auth_manager
        self.user_service = user_service

    @POST("/login")
    async def login(self, ctx: RequestCtx):
        """
        Login with username and password.
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

    @POST("/mfa/enroll")
    async def enroll_mfa(self, ctx: RequestCtx):
        """
        Enroll current user in TOTP MFA.
        """
        if not hasattr(ctx, "identity") or not ctx.identity:
            return Response.json({"error": "Auth required"}, status=401)
            
        # Simplified: Use a mock MFAManager
        mfa = MFAManager(totp_provider=TOTPProvider(issuer="MyApp"))
        enrollment = await mfa.enroll_totp(ctx.identity.id, ctx.identity.get_attribute("username"))
        
        # In a real app, we'd save the secret to the identity store
        # Here we just return it for testing
        return Response.json(enrollment)

    @POST("/mfa/verify")
    async def verify_mfa(self, ctx: RequestCtx):
        """
        Verify TOTP code.
        """
        data = await ctx.json()
        secret = data.get("secret")
        code = data.get("code")
        
        if not secret or not code:
            return Response.json({"error": "Missing secret or code"}, status=400)
            
        mfa = MFAManager(totp_provider=TOTPProvider())
        is_valid = await mfa.verify_totp(secret, code)
        
        if is_valid:
            return Response.json({"status": "verified"})
        return Response.json({"error": "Invalid code"}, status=400)
