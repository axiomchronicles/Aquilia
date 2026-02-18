"""
CRM Auth Service — Registration, login, token management.
Fully wired through the Aquilia ORM — all queries use
Model.objects / Model.create() / instance.save().
"""

from typing import Optional, Dict, Any
from aquilia.di import service
from aquilia.auth import (
    AuthManager,
    Identity,
    IdentityType,
    IdentityStatus,
    PasswordHasher,
    PasswordCredential,
)
from aquilia.cache import CacheService

from modules.shared.models import User
from modules.shared.faults import (
    InvalidCredentialsFault,
    UserAlreadyExistsFault,
    UnauthorizedFault,
)


@service(scope="app")
class CRMAuthService:
    """
    Authentication service for the CRM.
    All persistence goes through the Aquilia ORM (Model.objects API).
    The framework wires the DB during _boot_models() via
    ModelRegistry.set_database(), so Model._db is always available.
    """

    def __init__(
        self,
        auth_manager: AuthManager = None,
        cache: CacheService = None,
    ):
        self.auth_manager = auth_manager
        self.cache = cache
        self.hasher = PasswordHasher()

    async def register(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Register a new CRM user."""
        email = data["email"].lower().strip()

        # Check duplicate via ORM
        existing = await User.objects.filter(email=email).exists()
        if existing:
            raise UserAlreadyExistsFault(email)

        pw_hash = self.hasher.hash(data["password"])
        first_name = data["first_name"]
        last_name = data["last_name"]
        role = data.get("role", "rep")

        # Create user via ORM — auto_now_add handles timestamps
        user = await User.create(
            email=email,
            password_hash=pw_hash,
            first_name=first_name,
            last_name=last_name,
            role=role,
            is_active=True,
        )

        # Register identity + credential with AuthManager for token support
        if self.auth_manager:
            identity = Identity(
                id=str(user.pk),
                type=IdentityType.USER,
                attributes={
                    "email": email,
                    "roles": [role],
                    "name": f"{first_name} {last_name}",
                },
                status=IdentityStatus.ACTIVE,
            )
            await self.auth_manager.identity_store.create(identity)
            await self.auth_manager.credential_store.save_password(
                PasswordCredential(
                    identity_id=str(user.pk),
                    password_hash=pw_hash,
                )
            )

        return user.to_safe_dict()

    async def login(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticate user and return tokens."""
        email = email.lower().strip()

        # Find active user via ORM
        user = await User.objects.filter(email=email, is_active=True).first()
        if not user:
            raise InvalidCredentialsFault()

        if not self.hasher.verify(user.password_hash, password):
            raise InvalidCredentialsFault()

        tokens = {}
        if self.auth_manager and hasattr(self.auth_manager, "token_manager"):
            tm = self.auth_manager.token_manager
            roles = [user.role] if hasattr(user, "role") else ["rep"]

            access_token = await tm.issue_access_token(
                identity_id=str(user.pk),
                scopes=["crm:read", "crm:write"],
                roles=roles,
            )
            refresh_token = await tm.issue_refresh_token(
                identity_id=str(user.pk),
                scopes=["crm:read", "crm:write"],
            )
            tokens = {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
            }

        # Update last login via ORM instance save
        from datetime import datetime, timezone

        user.last_login = datetime.now(timezone.utc).isoformat()
        await user.save(update_fields=["last_login"])

        return {
            "user": user.to_safe_dict(),
            "tokens": tokens,
        }

    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID with caching."""
        cache_key = f"user:{user_id}"

        if self.cache:
            cached = await self.cache.get(cache_key)
            if cached:
                return cached

        user = await User.get(pk=user_id)
        if not user:
            return None

        result = user.to_safe_dict()

        if self.cache:
            await self.cache.set(cache_key, result, ttl=300)

        return result

    async def get_all_users(self) -> list:
        """Get all active users."""
        users = await User.objects.filter(is_active=True).order("-created_at").all()
        return [u.to_safe_dict() for u in users]

    async def update_profile(self, user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update user profile via ORM instance save."""
        user = await User.get(pk=user_id)
        if not user:
            return None

        changed = []
        for key in ("first_name", "last_name", "phone", "avatar_url"):
            if key in data and data[key] is not None:
                setattr(user, key, data[key])
                changed.append(key)

        if changed:
            await user.save(update_fields=changed)

        if self.cache:
            await self.cache.delete(f"user:{user_id}")

        return user.to_safe_dict()
