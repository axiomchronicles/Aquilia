"""
AquilAuth - Guards and Flow Integration

Guards for authentication and authorization that integrate with Flow Engine.
Decorators and middleware for protecting routes.
"""

from __future__ import annotations

import functools
from typing import Any, Callable, Coroutine

from .authz import AuthzContext, AuthzEngine
from .core import Identity
from .faults import AUTH_REQUIRED, AUTH_TOKEN_INVALID
from .manager import AuthManager


# ============================================================================
# Guard Base
# ============================================================================


class Guard:
    """
    Base guard for authentication/authorization.

    Guards are Flow pipeline nodes that enforce security policies.
    """

    async def __call__(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Execute guard.

        Args:
            context: Flow context

        Returns:
            Modified context

        Raises:
            AUTH_* or AUTHZ_* faults on failure
        """
        raise NotImplementedError


# ============================================================================
# Authentication Guards
# ============================================================================


class AuthGuard(Guard):
    """
    Authentication guard - requires valid authentication.

    Extracts identity from token and injects into context.
    """

    def __init__(self, auth_manager: AuthManager, optional: bool = False):
        """
        Initialize auth guard.

        Args:
            auth_manager: Authentication manager
            optional: If True, don't raise on missing auth
        """
        self.auth_manager = auth_manager
        self.optional = optional

    async def __call__(self, context: dict[str, Any]) -> dict[str, Any]:
        """Extract and verify authentication."""
        # Extract token from context (request headers)
        request = context.get("request")
        if not request:
            if self.optional:
                context["identity"] = None
                return context
            raise AUTH_REQUIRED()

        # Get Authorization header
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            if self.optional:
                context["identity"] = None
                return context
            raise AUTH_REQUIRED()

        token = auth_header[7:]  # Remove "Bearer "

        try:
            # Verify token and get identity
            identity = await self.auth_manager.get_identity_from_token(token)

            if not identity:
                if self.optional:
                    context["identity"] = None
                    return context
                raise AUTH_TOKEN_INVALID()

            # Inject identity into context
            context["identity"] = identity
            context["token_claims"] = await self.auth_manager.verify_token(
                token
            )

        except Exception as e:
            if self.optional:
                context["identity"] = None
                return context
            raise

        return context


class ApiKeyGuard(Guard):
    """
    API key authentication guard.

    Extracts API key and authenticates.
    """

    def __init__(self, auth_manager: AuthManager, required_scopes: list[str] | None = None):
        """
        Initialize API key guard.

        Args:
            auth_manager: Authentication manager
            required_scopes: Required scopes for this endpoint
        """
        self.auth_manager = auth_manager
        self.required_scopes = required_scopes

    async def __call__(self, context: dict[str, Any]) -> dict[str, Any]:
        """Extract and verify API key."""
        request = context.get("request")
        if not request:
            raise AUTH_REQUIRED()

        # Get API key from header
        api_key = request.headers.get("x-api-key")
        if not api_key:
            raise AUTH_REQUIRED()

        # Authenticate with API key
        auth_result = await self.auth_manager.authenticate_api_key(
            api_key=api_key,
            required_scopes=self.required_scopes,
        )

        # Inject identity into context
        context["identity"] = auth_result.identity
        context["api_key_scopes"] = auth_result.metadata.get("scopes", [])

        return context


# ============================================================================
# Authorization Guards
# ============================================================================


class AuthzGuard(Guard):
    """
    Authorization guard - enforces access control.

    Requires AuthGuard to run first (needs identity in context).
    """

    def __init__(
        self,
        authz_engine: AuthzEngine,
        resource_extractor: Callable[[dict[str, Any]], str] | None = None,
        action: str | None = None,
        required_scopes: list[str] | None = None,
        required_roles: list[str] | None = None,
        policy_id: str | None = None,
    ):
        """
        Initialize authorization guard.

        Args:
            authz_engine: Authorization engine
            resource_extractor: Function to extract resource from context
            action: Action being performed
            required_scopes: Required OAuth scopes
            required_roles: Required roles
            policy_id: Policy to evaluate
        """
        self.authz_engine = authz_engine
        self.resource_extractor = resource_extractor
        self.action = action
        self.required_scopes = required_scopes
        self.required_roles = required_roles
        self.policy_id = policy_id

    async def __call__(self, context: dict[str, Any]) -> dict[str, Any]:
        """Check authorization."""
        # Get identity from context (injected by AuthGuard)
        identity = context.get("identity")
        if not identity:
            raise AUTH_REQUIRED()

        # Extract resource identifier
        resource = "unknown"
        if self.resource_extractor:
            resource = self.resource_extractor(context)
        elif "resource" in context:
            resource = context["resource"]

        # Get token claims for scopes/roles
        token_claims = context.get("token_claims")
        scopes = token_claims.scopes if token_claims else []
        roles = token_claims.roles if token_claims else []

        # Build authorization context
        authz_context = AuthzContext(
            identity=identity,
            resource=resource,
            action=self.action or context.get("action", "access"),
            scopes=scopes,
            roles=roles,
            tenant_id=identity.tenant_id,
            session_id=token_claims.sid if token_claims else None,
            attributes=context.get("resource_attributes", {}),
        )

        # Check scopes
        if self.required_scopes:
            self.authz_engine.check_scope(authz_context, self.required_scopes)

        # Check roles
        if self.required_roles:
            self.authz_engine.check_role(authz_context, self.required_roles)

        # Evaluate policy
        if self.policy_id:
            result = self.authz_engine.abac.evaluate(
                authz_context, self.policy_id
            )
            if result.decision.value == "deny":
                from .faults import AUTHZ_POLICY_DENIED

                raise AUTHZ_POLICY_DENIED(
                    policy_id=self.policy_id,
                    denial_reason=result.reason or "Access denied",
                )

        # Store authorization result in context
        context["authz_context"] = authz_context

        return context


class ScopeGuard(Guard):
    """
    Scope-only guard - quick scope check.

    Simpler than full AuthzGuard when only scopes matter.
    """

    def __init__(self, required_scopes: list[str]):
        """
        Initialize scope guard.

        Args:
            required_scopes: Required OAuth scopes
        """
        self.required_scopes = required_scopes

    async def __call__(self, context: dict[str, Any]) -> dict[str, Any]:
        """Check scopes."""
        token_claims = context.get("token_claims")
        if not token_claims:
            raise AUTH_REQUIRED()

        from .faults import AUTHZ_INSUFFICIENT_SCOPE

        missing_scopes = set(self.required_scopes) - set(token_claims.scopes)
        if missing_scopes:
            raise AUTHZ_INSUFFICIENT_SCOPE(
                required_scopes=self.required_scopes,
                available_scopes=token_claims.scopes,
            )

        return context


class RoleGuard(Guard):
    """
    Role-only guard - quick role check.

    Simpler than full AuthzGuard when only roles matter.
    """

    def __init__(self, required_roles: list[str], require_all: bool = False):
        """
        Initialize role guard.

        Args:
            required_roles: Required roles
            require_all: If True, require all roles; else require any
        """
        self.required_roles = required_roles
        self.require_all = require_all

    async def __call__(self, context: dict[str, Any]) -> dict[str, Any]:
        """Check roles."""
        token_claims = context.get("token_claims")
        if not token_claims:
            raise AUTH_REQUIRED()

        from .faults import AUTHZ_INSUFFICIENT_ROLE

        user_roles = set(token_claims.roles)
        required = set(self.required_roles)

        if self.require_all:
            if not required.issubset(user_roles):
                raise AUTHZ_INSUFFICIENT_ROLE(
                    required_roles=self.required_roles,
                    available_roles=token_claims.roles,
                )
        else:
            if not required.intersection(user_roles):
                raise AUTHZ_INSUFFICIENT_ROLE(
                    required_roles=self.required_roles,
                    available_roles=token_claims.roles,
                )

        return context


# ============================================================================
# Decorators
# ============================================================================


def require_auth(
    auth_manager: AuthManager, optional: bool = False
) -> Callable:
    """
    Decorator: Require authentication.

    Args:
        auth_manager: Authentication manager
        optional: If True, don't raise on missing auth

    Example:
        @require_auth(auth_manager)
        async def get_profile(request, identity: Identity):
            return {"user": identity.id}
    """

    def decorator(
        func: Callable[..., Coroutine[Any, Any, Any]]
    ) -> Callable[..., Coroutine[Any, Any, Any]]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from args
            request = args[0] if args else kwargs.get("request")

            # Get Authorization header
            auth_header = getattr(request, "headers", {}).get(
                "authorization", ""
            )
            if not auth_header.startswith("Bearer "):
                if optional:
                    kwargs["identity"] = None
                    return await func(*args, **kwargs)
                raise AUTH_REQUIRED()

            token = auth_header[7:]

            # Verify and get identity
            identity = await auth_manager.get_identity_from_token(token)
            if not identity and not optional:
                raise AUTH_TOKEN_INVALID()

            # Inject identity
            kwargs["identity"] = identity
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_scopes(*scopes: str) -> Callable:
    """
    Decorator: Require OAuth scopes.

    Args:
        *scopes: Required scopes

    Example:
        @require_scopes("orders.read", "orders.write")
        async def create_order(request, identity: Identity):
            ...
    """

    def decorator(
        func: Callable[..., Coroutine[Any, Any, Any]]
    ) -> Callable[..., Coroutine[Any, Any, Any]]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Get token_claims from kwargs (injected by require_auth)
            token_claims = kwargs.get("token_claims")
            if not token_claims:
                raise AUTH_REQUIRED()

            from .faults import AUTHZ_INSUFFICIENT_SCOPE

            missing = set(scopes) - set(token_claims.scopes)
            if missing:
                raise AUTHZ_INSUFFICIENT_SCOPE(
                    required_scopes=list(scopes),
                    available_scopes=token_claims.scopes,
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_roles(*roles: str, require_all: bool = False) -> Callable:
    """
    Decorator: Require roles.

    Args:
        *roles: Required roles
        require_all: If True, require all roles; else require any

    Example:
        @require_roles("admin", "moderator")
        async def ban_user(request, identity: Identity):
            ...
    """

    def decorator(
        func: Callable[..., Coroutine[Any, Any, Any]]
    ) -> Callable[..., Coroutine[Any, Any, Any]]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            token_claims = kwargs.get("token_claims")
            if not token_claims:
                raise AUTH_REQUIRED()

            from .faults import AUTHZ_INSUFFICIENT_ROLE

            user_roles = set(token_claims.roles)
            required = set(roles)

            if require_all:
                if not required.issubset(user_roles):
                    raise AUTHZ_INSUFFICIENT_ROLE(
                        required_roles=list(roles),
                        available_roles=token_claims.roles,
                    )
            else:
                if not required.intersection(user_roles):
                    raise AUTHZ_INSUFFICIENT_ROLE(
                        required_roles=list(roles),
                        available_roles=token_claims.roles,
                    )

            return await func(*args, **kwargs)

        return wrapper

    return decorator
