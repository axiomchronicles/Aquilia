"""
Aquilia Testing - Auth & Identity Helpers.

Provides :class:`AuthTestMixin` for authenticating test clients,
and :class:`TestIdentityFactory` for creating test identities
with a fluent builder API.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from aquilia.auth.core import Identity, IdentityType, IdentityStatus


class TestIdentityFactory:
    """
    Factory for creating test identities with sensible defaults.

    Usage::

        factory = TestIdentityFactory()
        admin = factory.admin(id="admin-1")
        user = factory.user(email="alice@test.com")
        api_key = factory.service(scopes=["read:users"])

        # Builder pattern:
        identity = factory.build("u-1").with_roles("admin").with_scopes("*").create()
    """

    _counter = 0

    @classmethod
    def _next_id(cls) -> str:
        cls._counter += 1
        return f"test-user-{cls._counter}"

    @classmethod
    def user(
        cls,
        id: Optional[str] = None,
        email: Optional[str] = None,
        name: Optional[str] = None,
        roles: Optional[List[str]] = None,
        scopes: Optional[List[str]] = None,
        status: IdentityStatus = IdentityStatus.ACTIVE,
        tenant_id: Optional[str] = None,
        **extra_attrs: Any,
    ) -> Identity:
        """Create a regular user identity."""
        uid = id or cls._next_id()
        attrs = {
            "email": email or f"{uid}@test.com",
            "display_name": name or f"Test User {uid}",
            "roles": roles or ["user"],
            "scopes": scopes or [],
        }
        attrs.update(extra_attrs)
        return Identity(
            id=uid,
            type=IdentityType.USER,
            status=status,
            attributes=attrs,
            tenant_id=tenant_id,
        )

    @classmethod
    def admin(cls, id: Optional[str] = None, **kw) -> Identity:
        """Create an admin identity."""
        kw.setdefault("roles", ["admin", "user"])
        kw.setdefault("scopes", ["*"])
        return cls.user(id=id, **kw)

    @classmethod
    def service(
        cls,
        id: Optional[str] = None,
        scopes: Optional[List[str]] = None,
        **kw,
    ) -> Identity:
        """Create a service/API-key identity."""
        uid = id or f"service-{cls._next_id()}"
        attrs = {
            "scopes": scopes or [],
            "display_name": f"Service {uid}",
        }
        attrs.update(kw)
        return Identity(
            id=uid,
            type=IdentityType.SERVICE,
            status=IdentityStatus.ACTIVE,
            attributes=attrs,
        )

    @classmethod
    def anonymous(cls) -> Identity:
        """Create an anonymous (unauthenticated) identity."""
        return Identity(
            id="anonymous",
            type=IdentityType.USER,
            status=IdentityStatus.ACTIVE,
            attributes={"roles": [], "scopes": []},
        )

    @classmethod
    def suspended(cls, id: Optional[str] = None, **kw) -> Identity:
        """Create a suspended user identity."""
        return cls.user(id=id, status=IdentityStatus.SUSPENDED, **kw)

    @classmethod
    def build(cls, id: Optional[str] = None) -> "IdentityBuilder":
        """Start building an identity with the fluent API."""
        return IdentityBuilder(id or cls._next_id())


class IdentityBuilder:
    """
    Fluent builder for constructing test identities.

    Usage::

        identity = (
            TestIdentityFactory.build("u-1")
            .with_roles("admin", "editor")
            .with_scopes("read:*", "write:*")
            .with_email("admin@test.com")
            .with_tenant("org-1")
            .create()
        )
    """

    def __init__(self, id: str):
        self._id = id
        self._type = IdentityType.USER
        self._status = IdentityStatus.ACTIVE
        self._roles: List[str] = ["user"]
        self._scopes: List[str] = []
        self._email: Optional[str] = None
        self._name: Optional[str] = None
        self._tenant_id: Optional[str] = None
        self._extra: Dict[str, Any] = {}

    def with_roles(self, *roles: str) -> "IdentityBuilder":
        self._roles = list(roles)
        return self

    def with_scopes(self, *scopes: str) -> "IdentityBuilder":
        self._scopes = list(scopes)
        return self

    def with_email(self, email: str) -> "IdentityBuilder":
        self._email = email
        return self

    def with_name(self, name: str) -> "IdentityBuilder":
        self._name = name
        return self

    def with_tenant(self, tenant_id: str) -> "IdentityBuilder":
        self._tenant_id = tenant_id
        return self

    def with_status(self, status: IdentityStatus) -> "IdentityBuilder":
        self._status = status
        return self

    def with_type(self, type: IdentityType) -> "IdentityBuilder":
        self._type = type
        return self

    def with_attr(self, key: str, value: Any) -> "IdentityBuilder":
        self._extra[key] = value
        return self

    def as_service(self) -> "IdentityBuilder":
        self._type = IdentityType.SERVICE
        return self

    def as_suspended(self) -> "IdentityBuilder":
        self._status = IdentityStatus.SUSPENDED
        return self

    def create(self) -> Identity:
        """Build and return the Identity."""
        attrs = {
            "email": self._email or f"{self._id}@test.com",
            "display_name": self._name or f"Test User {self._id}",
            "roles": self._roles,
            "scopes": self._scopes,
        }
        attrs.update(self._extra)
        return Identity(
            id=self._id,
            type=self._type,
            status=self._status,
            attributes=attrs,
            tenant_id=self._tenant_id,
        )


class AuthTestMixin:
    """
    Mixin providing authentication helpers for test cases.

    Expects ``self.client`` (:class:`TestClient`) and optionally
    ``self.server`` (:class:`TestServer`).

    Usage::

        class TestProtectedAPI(AquiliaTestCase, AuthTestMixin):
            enable_auth = True

            async def test_admin_only(self):
                self.force_login(TestIdentityFactory.admin())
                resp = await self.client.get("/admin/dashboard")
                self.assert_status(resp, 200)
    """

    _forced_identities: Dict[str, Identity]

    def force_login(self, identity: Identity) -> None:
        """
        Bypass the normal auth flow and inject an identity into the
        test client so subsequent requests appear authenticated.

        Works by setting a header that the test middleware recognises,
        or by directly setting session/identity state.
        """
        # Attach identity to client headers so the request-scope
        # middleware can pick it up
        if hasattr(self, "client"):
            self.client._default_headers["X-Test-Identity-Id"] = identity.id
            # Store the identity for the test auth middleware
            if not hasattr(self, "_forced_identities"):
                self._forced_identities = {}
            self._forced_identities[identity.id] = identity

    def force_logout(self) -> None:
        """Remove any forced authentication."""
        if hasattr(self, "client"):
            self.client._default_headers.pop("X-Test-Identity-Id", None)
        if hasattr(self, "_forced_identities"):
            self._forced_identities.clear()

    @property
    def current_identity(self) -> Optional[Identity]:
        """Return the currently forced identity (or None)."""
        if not hasattr(self, "_forced_identities") or not self._forced_identities:
            return None
        if hasattr(self, "client"):
            identity_id = self.client._default_headers.get("X-Test-Identity-Id")
            if identity_id and identity_id in self._forced_identities:
                return self._forced_identities[identity_id]
        # Return last forced identity
        return next(reversed(self._forced_identities.values()), None)

    @property
    def is_authenticated(self) -> bool:
        """Check if a test identity is currently forced."""
        return self.current_identity is not None

    async def authenticate_as(
        self,
        identity: Identity,
    ) -> None:
        """
        Authenticate by injecting the identity into the DI container.

        This is more thorough than ``force_login`` — it actually registers
        the identity in the request scope so DI-resolved services see it.
        """
        self.force_login(identity)

        # If the server has an auth manager, register the identity
        if hasattr(self, "server") and self.server.auth_manager:
            store = self.server.auth_manager.identity_store
            if hasattr(store, "_identities"):
                store._identities[identity.id] = identity

    def login_as_admin(self, id: Optional[str] = None, **kw) -> Identity:
        """Convenience: create admin identity and force login."""
        identity = TestIdentityFactory.admin(id=id, **kw)
        self.force_login(identity)
        return identity

    def login_as_user(self, id: Optional[str] = None, **kw) -> Identity:
        """Convenience: create user identity and force login."""
        identity = TestIdentityFactory.user(id=id, **kw)
        self.force_login(identity)
        return identity
