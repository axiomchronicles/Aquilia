"""
Auth module services (business logic).

Services contain the core business logic and are auto-wired
via dependency injection.
"""

from typing import Optional, List, Dict, Any
from aquilia.di import service
from aquilia.auth.tokens import TokenManager, KeyRing, TokenStore, KeyDescriptor
from aquilia.auth.hashing import PasswordHasher
from aquilia.cache import CacheService, get_default_cache_service
from .models import User
from .faults import UserAlreadyExistsFault, InvalidCredentialsFault, AuthNotFoundFault
from pathlib import Path
import uuid
from aquilia._uploads import UploadFile

_STABLE_KEY: Optional[KeyDescriptor] = None # Module-level stable key for dev/debugging

# Simple in-memory token store for demonstration/MVP
# In production, this should likely be Redis or DB backed
class InMemoryTokenStore(TokenStore):
    def __init__(self):
        self._refresh_tokens = {}
        self._revoked_tokens = set()

    async def save_refresh_token(
        self,
        token_id: str,
        identity_id: str,
        scopes: list[str],
        expires_at: Any,
        session_id: str | None = None,
    ) -> None:
        self._refresh_tokens[token_id] = {
            "token_id": token_id,
            "identity_id": identity_id,
            "scopes": scopes,
            "expires_at": expires_at.isoformat(),
            "session_id": session_id,
        }

    async def get_refresh_token(self, token_id: str) -> dict[str, Any] | None:
        return self._refresh_tokens.get(token_id)

    async def revoke_refresh_token(self, token_id: str) -> None:
        if token_id in self._refresh_tokens:
            del self._refresh_tokens[token_id]
        self._revoked_tokens.add(token_id)

    async def revoke_tokens_by_identity(self, identity_id: str) -> None:
        # Simplistic implementation
        to_remove = []
        for tid, data in self._refresh_tokens.items():
            if data["identity_id"] == identity_id:
                to_remove.append(tid)
        for tid in to_remove:
            del self._refresh_tokens[tid]

    async def revoke_tokens_by_session(self, session_id: str) -> None:
        to_remove = []
        for tid, data in self._refresh_tokens.items():
            if data["session_id"] == session_id:
                to_remove.append(tid)
        for tid in to_remove:
            del self._refresh_tokens[tid]

    async def is_token_revoked(self, token_id: str) -> bool:
        return token_id in self._revoked_tokens


@service(scope="app")
class AuthService:
    """
    Service for auth business logic.
    """

    def __init__(self, cache: CacheService = None):
        self.token_store = InMemoryTokenStore()
        
        # Static key logic for development
        global _STABLE_KEY
        key_path = Path(__file__).parent.parent.parent / "auth_keys.json"
        
        if _STABLE_KEY is None:
            if key_path.exists():
                try:
                    ring = KeyRing.from_file(key_path)
                    _STABLE_KEY = ring.get_signing_key()
                except Exception:
                    _STABLE_KEY = KeyDescriptor.generate("auth-key-1")
                    KeyRing([_STABLE_KEY]).to_file(key_path)
            else:
                _STABLE_KEY = KeyDescriptor.generate("auth-key-1")
                KeyRing([_STABLE_KEY]).to_file(key_path)
            
        key_ring = KeyRing([_STABLE_KEY])
        self.token_manager = TokenManager(key_ring, self.token_store)
        self.hasher = PasswordHasher()
        # Default to memory cache if not provided via DI
        self.cache = cache or get_default_cache_service()

    async def register(self, data: dict) -> Dict[str, Any]:
        """Register a new user."""
        profile = data.get("profile")
        email = data.get("email")
        password = data.get("password")
        full_name = data.get("full_name")
        
        # Check if user exists
        existing = await User.get(email=email)
        if existing:
            raise UserAlreadyExistsFault(email=email)

        # Hash password
        password_hash = self.hasher.hash(password)

        profile_path = None
        if isinstance(profile, UploadFile) and profile.filename:
            # Save profile photo
            file_ext = Path(profile.filename).suffix
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            save_path = Path("authentication/uploads/profiles") / unique_filename
            
            # Ensure directory exists (just in case)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            await profile.save(save_path)
            profile_path = f"/uploads/profiles/{unique_filename}"

        # Create user
        user = await User.create(
            profile=profile_path,
            email=email,
            password_hash=password_hash,
            full_name=full_name
        )

        return {
            "id": user.id,
            "profile": user.profile,
            "email": user.email,
            "full_name": user.full_name,
            "created_at": user.created_at.isoformat()
        }

    async def login(self, data: dict) -> Dict[str, Any]:
        """Login and return tokens."""
        email = data.get("email")
        password = data.get("password")

        user = await User.get(email=email)
        if user and self.hasher.verify(user.password_hash, password):
            pass # Success
        else:
            raise InvalidCredentialsFault()

        # Issue tokens
        access_token = await self.token_manager.issue_access_token(
            identity_id=str(user.id),
            scopes=["user"],
            roles=["admin"] if user.is_superuser else ["user"]
        )
        refresh_token = await self.token_manager.issue_refresh_token(
            identity_id=str(user.id),
            scopes=["user"]
        )
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": 3600 # Default TTL
        }
    
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token."""
        try:
            access_token, new_refresh_token = await self.token_manager.refresh_access_token(refresh_token)
            return {
                "access_token": access_token,
                "refresh_token": new_refresh_token,
                "token_type": "Bearer",
                "expires_in": 3600
            }
        except ValueError:
             raise InvalidCredentialsFault() # Or a specific token fault

    async def get_current_user_from_token(self, token: str) -> Dict[str, Any]:
        """Validate token and get user (cached)."""
        try:
            payload = await self.token_manager.validate_access_token(token)
            user_id = payload.get("sub")
            
            # 1. Try Cache
            cache_key = f"user:{user_id}"
            if self.cache:
                cached_user = await self.cache.get(cache_key)
                if cached_user:
                    return cached_user

            # 2. Fetch from DB
            user = await User.get(pk=int(user_id))
            if not user:
                raise AuthNotFoundFault(item_id=user_id)
            
            user_data = {
                "id": user.id,
                "email": user.email,
                "profile": user.profile,
                "full_name": user.full_name,
                "created_at": user.created_at.isoformat()
            }
            
            # 3. Store in Cache (TTL=300s)
            if self.cache:
                await self.cache.set(cache_key, user_data, ttl=300)
            
            return user_data
        except Exception as e:
            import logging
            logger = logging.getLogger("auth")
            logger.error(f"Error in get_current_user_from_token: {e}", exc_info=True)
            # Re-raise as auth fault or return None
            raise AuthNotFoundFault(item_id=0) # Generic fail