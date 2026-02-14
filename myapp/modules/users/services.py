"""
Users Module - Services (Business Logic)

Showcases:
- @service decorator with DI scoping
- Constructor injection
- Password hashing integration
- Identity management
- Token issuance
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import secrets
import hashlib

from aquilia.di import service
from aquilia.auth import (
    Identity,
    IdentityType,
    IdentityStatus,
    PasswordHasher,
    PasswordPolicy,
)


@service(scope="app")
class UserRepository:
    """
    User data repository.

    App-scoped: single instance shared across all requests.
    Demonstrates in-memory storage (swap for real DB in production).
    """

    def __init__(self):
        self._users: Dict[str, Dict[str, Any]] = {}
        self._next_id = 1

    async def find_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self._users.get(user_id)

    async def find_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        for user in self._users.values():
            if user["email"] == email:
                return user
        return None

    async def find_all(self) -> List[Dict[str, Any]]:
        return list(self._users.values())

    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        user_id = str(self._next_id)
        self._next_id += 1
        user = {
            "id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            **data,
        }
        self._users[user_id] = user
        return user

    async def update(self, user_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if user_id not in self._users:
            return None
        self._users[user_id].update(data)
        self._users[user_id]["updated_at"] = datetime.utcnow().isoformat()
        return self._users[user_id]

    async def delete(self, user_id: str) -> bool:
        return self._users.pop(user_id, None) is not None


@service(scope="app")
class TokenService:
    """
    Simple token service for authentication.

    Demonstrates app-scoped service with in-memory token storage.
    In production, use aquilia.auth.TokenManager with JWT + KeyRing.
    """

    def __init__(self):
        self._tokens: Dict[str, Dict[str, Any]] = {}

    async def create_token(self, user_id: str, scopes: List[str] = None) -> str:
        """Issue a new access token."""
        token = secrets.token_urlsafe(32)
        self._tokens[token] = {
            "user_id": user_id,
            "scopes": scopes or ["read"],
            "issued_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
        }
        return token

    async def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate and return token claims."""
        claims = self._tokens.get(token)
        if not claims:
            return None
        # Check expiry
        expires = datetime.fromisoformat(claims["expires_at"])
        if datetime.utcnow() > expires:
            del self._tokens[token]
            return None
        return claims

    async def revoke_token(self, token: str) -> bool:
        """Revoke a token."""
        return self._tokens.pop(token, None) is not None


@service(scope="app")
class UserService:
    """
    User business logic service.

    Demonstrates:
    - Constructor injection (UserRepository is auto-injected)
    - Password hashing with PasswordHasher
    - Identity creation for auth
    """

    def __init__(self, repo: UserRepository = None, tokens: TokenService = None):
        self.repo = repo or UserRepository()
        self.tokens = tokens or TokenService()
        self.hasher = PasswordHasher()

    async def register(self, email: str, password: str, name: str, role: str = "user") -> Dict[str, Any]:
        """Register a new user with hashed password."""
        # Check if email exists
        existing = await self.repo.find_by_email(email)
        if existing:
            return {"error": "Email already registered"}

        # Hash password
        password_hash = await self.hasher.hash(password)

        # Create user
        user = await self.repo.create({
            "email": email,
            "name": name,
            "password_hash": password_hash,
            "role": role,
            "is_active": True,
        })

        # Return safe user data (no password hash)
        return self._safe_user(user)

    async def login(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user and return token."""
        user = await self.repo.find_by_email(email)
        if not user:
            return None

        # Verify password
        valid = await self.hasher.verify(password, user["password_hash"])
        if not valid:
            return None

        # Issue token
        token = await self.tokens.create_token(
            user_id=user["id"],
            scopes=["read", "write"] if user["role"] == "admin" else ["read"],
        )

        return {
            "token": token,
            "user": self._safe_user(user),
        }

    async def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile."""
        user = await self.repo.find_by_id(user_id)
        if not user:
            return None
        return self._safe_user(user)

    async def update_profile(self, user_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update user profile (name only, not email/password)."""
        allowed = {k: v for k, v in data.items() if k in ("name",)}
        user = await self.repo.update(user_id, allowed)
        if not user:
            return None
        return self._safe_user(user)

    async def list_users(self) -> List[Dict[str, Any]]:
        """List all users (admin only)."""
        users = await self.repo.find_all()
        return [self._safe_user(u) for u in users]

    async def get_identity(self, user_id: str) -> Optional[Identity]:
        """Build an Identity object for auth context."""
        user = await self.repo.find_by_id(user_id)
        if not user:
            return None
        return Identity(
            id=user["id"],
            type=IdentityType.USER,
            status=IdentityStatus.ACTIVE if user.get("is_active") else IdentityStatus.SUSPENDED,
            attributes={
                "email": user["email"],
                "name": user["name"],
                "roles": [user.get("role", "user")],
                "scopes": ["read", "write"] if user.get("role") == "admin" else ["read"],
            },
        )

    def _safe_user(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """Return user data without sensitive fields."""
        return {k: v for k, v in user.items() if k != "password_hash"}
