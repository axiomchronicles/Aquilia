"""
Users Module — Services

DI-managed services wiring Aquilia Auth, Cache, Mail, Sessions,
and ORM into a cohesive user management layer.
"""

import uuid
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional

from aquilia.di import service, inject, Inject
from aquilia.auth import (
    AuthManager,
    PasswordHasher,
    Identity,
    IdentityType,
    IdentityStatus,
    Credential,
)
from aquilia.cache import CacheService, cached, invalidate
from aquilia.mail import EmailMessage
from aquilia.mail.service import MailService
from aquilia.models import Q
from aquilia.models.signals import pre_save, post_save

from .models import User, UserAddress, UserSession, UserRole
from .faults import (
    UserNotFoundFault,
    DuplicateEmailFault,
    DuplicateUsernameFault,
    InvalidCredentialsFault,
    AccountDeactivatedFault,
    AccountNotVerifiedFault,
    InsufficientPermissionsFault,
    ProfileUpdateFault,
)


@service(scope="app")
class UserService:
    """
    Core user service — CRUD, search, and lifecycle management.

    Integrates:
    - Aquilia ORM (QuerySet, Q, signals)
    - Aquilia Cache (@cached, @invalidate)
    - Aquilia Mail (welcome emails)
    - Aquilia DI (@service, @inject)
    """

    def __init__(
        self,
        cache: CacheService = Inject(CacheService),
        mail: MailService = Inject(MailService),
        hasher: PasswordHasher = Inject(PasswordHasher),
    ):
        self.cache = cache
        self.mail = mail
        self.hasher = hasher

    # ── Queries ──────────────────────────────────────────────

    @cached(ttl=300, namespace="users")
    async def get_by_id(self, user_id: int) -> User:
        user = await User.objects.filter(id=user_id).first()
        if not user:
            raise UserNotFoundFault(str(user_id))
        return user

    @cached(ttl=300, namespace="users")
    async def get_by_email(self, email: str) -> Optional[User]:
        return await User.objects.filter(email=email.lower()).first()

    @cached(ttl=300, namespace="users")
    async def get_by_username(self, username: str) -> Optional[User]:
        return await User.objects.filter(username=username.lower()).first()

    @cached(ttl=60, namespace="users:list")
    async def list_users(
        self,
        page: int = 1,
        page_size: int = 20,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> dict:
        qs = User.objects.get_queryset()
        if role:
            qs = qs.filter(role=role)
        if is_active is not None:
            qs = qs.filter(is_active=is_active)
        if search:
            qs = qs.filter(
                Q(email__icontains=search)
                | Q(username__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
            )
        total = await qs.count()
        offset = (page - 1) * page_size
        users = await qs[offset : offset + page_size].all()
        return {
            "items": users,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size,
        }

    # ── Mutations ────────────────────────────────────────────

    @invalidate(namespace="users:list")
    async def create_user(self, data: dict) -> User:
        email = data["email"].lower()
        username = data["username"].lower()

        # uniqueness checks
        if await User.objects.filter(email=email).exists():
            raise DuplicateEmailFault(email)
        if await User.objects.filter(username=username).exists():
            raise DuplicateUsernameFault()

        user = User(
            uuid=str(uuid.uuid4()),
            email=email,
            username=username,
            password_hash=self.hasher.hash(data["password"]),
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            role=data.get("role", UserRole.CUSTOMER),
        )
        await user.save()

        # send welcome email asynchronously
        asyncio.create_task(self._send_welcome_email(user))

        return user

    @invalidate(namespace="users")
    async def update_user(self, user_id: int, data: dict) -> User:
        user = await self.get_by_id(user_id)
        for field, value in data.items():
            if hasattr(user, field) and field not in ("id", "uuid", "email", "password_hash"):
                setattr(user, field, value)
        await user.save()
        return user

    @invalidate(namespace="users")
    async def deactivate_user(self, user_id: int) -> User:
        user = await self.get_by_id(user_id)
        user.is_active = False
        await user.save()
        return user

    @invalidate(namespace="users")
    async def change_role(self, user_id: int, new_role: str, actor_role: str) -> User:
        if actor_role != UserRole.SUPERADMIN:
            raise InsufficientPermissionsFault(UserRole.SUPERADMIN)
        user = await self.get_by_id(user_id)
        user.role = new_role
        await user.save()
        return user

    @invalidate(namespace="users")
    async def update_password(self, user_id: int, current_pw: str, new_pw: str) -> None:
        user = await self.get_by_id(user_id)
        if not self.hasher.verify(user.password_hash, current_pw):
            raise InvalidCredentialsFault()
        user.password_hash = self.hasher.hash(new_pw)
        await user.save()

    # ── Address Management ───────────────────────────────────

    async def list_addresses(self, user_id: int) -> list:
        return await UserAddress.objects.filter(user_id=user_id).all()

    async def add_address(self, user_id: int, data: dict) -> UserAddress:
        if data.get("is_default"):
            await UserAddress.objects.filter(
                user_id=user_id, is_default=True
            ).update(is_default=False)

        address = UserAddress(user_id=user_id, **data)
        await address.save()
        return address

    async def delete_address(self, user_id: int, address_id: int) -> None:
        addr = await UserAddress.objects.filter(
            id=address_id, user_id=user_id
        ).first()
        if addr:
            await addr.delete()

    # ── Internal helpers ─────────────────────────────────────

    async def _send_welcome_email(self, user: User) -> None:
        """Send welcome email via Aquilia MailService."""
        try:
            msg = EmailMessage(
                subject="Welcome to Nexus!",
                to=[user.email],
                body=f"Hello {user.full_name or user.username},\n\n"
                     f"Welcome to Nexus. Your account is ready.\n\n"
                     f"— The Nexus Team",
            )
            await self.mail.asend_mail(msg)
        except Exception:
            pass  # non-critical — logged by MailService


@service(scope="app")
class AuthService:
    """
    Authentication service — login, token issuance, session tracking.

    Integrates:
    - Aquilia AuthManager (password verification, rate limiting)
    - Aquilia Identity/Credentials (identity model)
    - Aquilia Cache (token blacklisting)
    - Aquilia Sessions (session lifecycle)
    """

    def __init__(
        self,
        users: UserService = Inject(UserService),
        auth_manager: AuthManager = Inject(AuthManager),
        hasher: PasswordHasher = Inject(PasswordHasher),
        cache: CacheService = Inject(CacheService),
    ):
        self.users = users
        self.auth_manager = auth_manager
        self.hasher = hasher
        self.cache = cache

    async def authenticate(self, email: str, password: str) -> dict:
        """Authenticate user and return token payload."""
        user = await self.users.get_by_email(email)
        if not user:
            raise InvalidCredentialsFault()

        if not user.is_active:
            raise AccountDeactivatedFault()

        if not self.hasher.verify(user.password_hash, password):
            raise InvalidCredentialsFault()

        # update login tracking
        user.last_login_at = datetime.now(timezone.utc)
        user.login_count += 1
        await user.save()

        # build Aquilia Identity
        identity = Identity(
            id=str(user.id),
            type=IdentityType.USER,
            status=IdentityStatus.ACTIVE,
            attributes={
                "roles": [user.role],
                "permissions": [],
                "username": user.username,
                "email": user.email,
            },
        )

        # Generate a simple token (base64-encoded identity for demo)
        import base64, json as _json
        token_payload = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role,
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=24)).timestamp()),
        }
        access_token = base64.urlsafe_b64encode(
            _json.dumps(token_payload).encode()
        ).decode()

        return {
            "access_token": access_token,
            "refresh_token": "",
            "token_type": "Bearer",
            "expires_in": 86400,
            "user": user,
        }

    async def logout(self, token: str) -> None:
        """Blacklist the current access token."""
        await self.cache.set(
            f"token:blacklist:{token}",
            "1",
            ttl=3600,
            namespace="auth",
        )

    async def record_session(
        self,
        user: User,
        session_id: str,
        ip_address: str,
        user_agent: str = "",
    ) -> UserSession:
        """Persist a session record for audit/security."""
        session = UserSession(
            user_id=user.id,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await session.save()
        return session

    async def revoke_session(self, user_id: int, session_id: str) -> None:
        """Revoke a specific session."""
        session = await UserSession.objects.filter(
            user_id=user_id, session_id=session_id
        ).first()
        if session:
            session.is_active = False
            await session.save()

    async def get_active_sessions(self, user_id: int) -> list:
        """List all active sessions for a user."""
        return await UserSession.objects.filter(
            user_id=user_id, is_active=True
        ).all()
