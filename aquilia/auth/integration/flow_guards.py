"""
AquilAuth - Flow Guards (Deep Integration)

Guards that properly integrate with Aquilia Flow pipeline.
These replace the standalone guards with deep Flow integration.

Flow Pipeline Structure:
1. Middleware (global)
2. Guards (authentication/authorization)
3. Transforms (data transformation)
4. Handler (business logic)
5. Post-hooks (response processing)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from aquilia.flow import FlowNode, FlowNodeType
from aquilia.request import Request
from aquilia.response import Response

from ..authz import AuthzContext, AuthzEngine
from ..core import Identity
from ..faults import (
    AUTH_REQUIRED,
    AUTH_TOKEN_INVALID,
    AUTHZ_INSUFFICIENT_SCOPE,
    AUTHZ_INSUFFICIENT_ROLE,
    AUTHZ_POLICY_DENIED,
)
from ..manager import AuthManager
from .aquila_sessions import get_identity_id, get_roles, get_scopes

if TYPE_CHECKING:
    from aquilia.sessions import Session


# ============================================================================
# Flow Context Extensions
# ============================================================================


def _get_request(context: Any) -> Request | None:
    if isinstance(context, dict):
        return context.get("request")
    return getattr(context, "request", None)

def get_session(context: Any) -> Session | None:
    """Extract session from flow context."""
    request = _get_request(context)
    if request and hasattr(request, "state"):
        return request.state.get("session")
    return None


def get_identity(context: Any) -> Identity | None:
    """Extract identity from flow context."""
    request = _get_request(context)
    if request and hasattr(request, "state"):
        return request.state.get("identity")
    return None


def set_identity(context: Any, identity: Identity | None) -> None:
    """Set identity in flow context."""
    request = _get_request(context)
    if request and hasattr(request, "state"):
        request.state["identity"] = identity
        request.state["authenticated"] = identity is not None
    
    # Also update context directly if it's a dict
    if isinstance(context, dict):
        context["authenticated"] = identity is not None


# ============================================================================
# Flow Guard Base
# ============================================================================


class FlowGuard:
    """
    Base class for Flow guards.
    
    Guards are Flow nodes that enforce security policies.
    They run before the handler and can:
    - Inspect request/session/identity
    - Modify flow context
    - Short-circuit with error response
    - Inject data for downstream nodes
    """
    
    async def __call__(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Execute guard logic.
        
        Args:
            context: Flow context with request, session, identity
            
        Returns:
            Modified context (or raises fault)
            
        Raises:
            Fault on security violation
        """
        raise NotImplementedError
    
    def as_flow_node(self, name: str | None = None, priority: int = 50) -> FlowNode:
        """
        Convert guard to FlowNode.
        
        Args:
            name: Node name
            priority: Node priority (lower = earlier)
            
        Returns:
            FlowNode instance
        """
        return FlowNode(
            type=FlowNodeType.GUARD,
            callable=self,
            name=name or self.__class__.__name__,
            priority=priority,
            effects=["security"],
        )


# ============================================================================
# Authentication Guards
# ============================================================================


def _set_authenticated(context: Any, value: bool) -> None:
    request = _get_request(context)
    if request and hasattr(request, "state"):
        request.state["authenticated"] = value
    
    if isinstance(context, dict):
        context["authenticated"] = value
    elif hasattr(context, "state") and isinstance(context.state, dict):
        # RequestCtx has state dict
        context.state["authenticated"] = value

# ... existing code ...

class RequireAuthGuard(FlowGuard):
    """
    Require valid authentication.
    
    Checks that request has authenticated identity.
    Works with middleware that populates request.state.identity.
    """
    
    def __init__(self, optional: bool = False):
        """
        Initialize guard.
        
        Args:
            optional: If True, don't raise on missing auth
        """
        self.optional = optional
    
    async def __call__(self, context: dict[str, Any]) -> dict[str, Any]:
        """Verify authentication."""
        identity = get_identity(context)
        
        if not identity and not self.optional:
            raise AUTH_REQUIRED()
        
        # Add authenticated flag to context
        _set_authenticated(context, identity is not None)
        
        return context



def _set_item(context: Any, key: str, value: Any) -> None:
    if isinstance(context, dict):
        context[key] = value
    elif hasattr(context, "state") and isinstance(context.state, dict):
        context.state[key] = value


class RequireSessionAuthGuard(FlowGuard):
    """
    Require authentication via session.
    
    Checks that session has valid identity binding.
    """
    
    def __init__(self, auth_manager: AuthManager):
        """
        Initialize guard.
        
        Args:
            auth_manager: AuthManager instance
        """
        self.auth_manager = auth_manager
    
    async def __call__(self, context: dict[str, Any]) -> dict[str, Any]:
        """Verify session authentication."""
        session = get_session(context)
        
        if not session:
            raise AUTH_REQUIRED()
        
        # Check if session has identity
        identity_id = get_identity_id(session)
        if not identity_id:
            raise AUTH_REQUIRED()
        
        # Load identity
        identity = await self.auth_manager.identity_store.get_identity(identity_id)
        if not identity:
            raise AUTH_TOKEN_INVALID()
        
        # Inject into context
        set_identity(context, identity)
        _set_authenticated(context, True)
        
        return context


class RequireTokenAuthGuard(FlowGuard):
    """
    Require authentication via Bearer token.
    
    Extracts and validates token from Authorization header.
    """
    
    def __init__(self, auth_manager: AuthManager):
        """
        Initialize guard.
        
        Args:
            auth_manager: AuthManager instance
        """
        self.auth_manager = auth_manager
    
    async def __call__(self, context: dict[str, Any]) -> dict[str, Any]:
        """Verify token authentication."""
        request = context.get("request")
        if not request:
            raise AUTH_REQUIRED()
        
        # Extract Bearer token
        auth_header = request.header("authorization", "")
        if not auth_header.startswith("Bearer "):
            raise AUTH_REQUIRED()
        
        token = auth_header[7:]
        
        # Verify token and get identity
        identity = await self.auth_manager.get_identity_from_token(token)
        if not identity:
            raise AUTH_TOKEN_INVALID()
        
        # Inject into context
        set_identity(context, identity)
        _set_authenticated(context, True)
        _set_item(context, "token_claims", await self.auth_manager.verify_token(token))
        
        return context


class RequireApiKeyGuard(FlowGuard):
    """
    Require authentication via API key.
    
    Extracts and validates API key from X-API-Key header.
    """
    
    def __init__(
        self,
        auth_manager: AuthManager,
        required_scopes: list[str] | None = None,
    ):
        """
        Initialize guard.
        
        Args:
            auth_manager: AuthManager instance
            required_scopes: Required scopes for this endpoint
        """
        self.auth_manager = auth_manager
        self.required_scopes = required_scopes
    
    async def __call__(self, context: dict[str, Any]) -> dict[str, Any]:
        """Verify API key authentication."""
        request = context.get("request")
        if not request:
            raise AUTH_REQUIRED()
        
        # Extract API key
        api_key = request.header("x-api-key")
        if not api_key:
            raise AUTH_REQUIRED()
        
        # Authenticate
        auth_result = await self.auth_manager.authenticate_api_key(
            api_key=api_key,
            required_scopes=self.required_scopes,
        )
        
        # Inject into context
        set_identity(context, auth_result.identity)
        _set_authenticated(context, True)
        
        return context


# ============================================================================
# Authorization Guards
# ============================================================================


class RequireScopesGuard(FlowGuard):
    """
    Require specific OAuth scopes.
    
    Checks that identity has all required scopes.
    """
    
    def __init__(self, *scopes: str, require_all: bool = True):
        """
        Initialize guard.
        
        Args:
            *scopes: Required scopes
            require_all: If True, require all scopes. If False, require any.
        """
        self.scopes = list(scopes)
        self.require_all = require_all
    
    async def __call__(self, context: dict[str, Any]) -> dict[str, Any]:
        """Verify scopes."""
        # First verify authentication
        identity = get_identity(context)
        if not identity:
            raise AUTH_REQUIRED()
        
        # Check scopes
        user_scopes = set(identity.scopes)
        required_scopes = set(self.scopes)
        
        if self.require_all:
            # Must have all required scopes
            if not required_scopes.issubset(user_scopes):
                missing = required_scopes - user_scopes
                raise AUTHZ_INSUFFICIENT_SCOPE(
                    required=list(required_scopes),
                    actual=list(user_scopes),
                    missing=list(missing),
                )
        else:
            # Must have at least one required scope
            if not required_scopes.intersection(user_scopes):
                raise AUTHZ_INSUFFICIENT_SCOPE(
                    required=list(required_scopes),
                    actual=list(user_scopes),
                )
        
        return context


class RequireRolesGuard(FlowGuard):
    """
    Require specific roles.
    
    Checks that identity has all required roles.
    """
    
    def __init__(self, *roles: str, require_all: bool = True):
        """
        Initialize guard.
        
        Args:
            *roles: Required roles
            require_all: If True, require all roles. If False, require any.
        """
        self.roles = list(roles)
        self.require_all = require_all
    
    async def __call__(self, context: dict[str, Any]) -> dict[str, Any]:
        """Verify roles."""
        # First verify authentication
        identity = get_identity(context)
        if not identity:
            raise AUTH_REQUIRED()
        
        # Check roles
        user_roles = set(identity.get_attribute("roles", []))
        required_roles = set(self.roles)
        
        if self.require_all:
            # Must have all required roles
            if not required_roles.issubset(user_roles):
                missing = required_roles - user_roles
                raise AUTHZ_INSUFFICIENT_ROLE(
                    required=list(required_roles),
                    actual=list(user_roles),
                    missing=list(missing),
                )
        else:
            # Must have at least one required role
            if not required_roles.intersection(user_roles):
                raise AUTHZ_INSUFFICIENT_ROLE(
                    required=list(required_roles),
                    actual=list(user_roles),
                )
        
        return context


class RequirePermissionGuard(FlowGuard):
    """
    Require specific permission.
    
    Uses AuthzEngine to check RBAC permission.
    """
    
    def __init__(
        self,
        authz_engine: AuthzEngine,
        permission: str,
        resource: str | None = None,
    ):
        """
        Initialize guard.
        
        Args:
            authz_engine: Authorization engine
            permission: Required permission (e.g., "orders:write")
            resource: Optional resource identifier
        """
        self.authz_engine = authz_engine
        self.permission = permission
        self.resource = resource
    
    async def __call__(self, context: dict[str, Any]) -> dict[str, Any]:
        """Verify permission."""
        # First verify authentication
        identity = get_identity(context)
        if not identity:
            raise AUTH_REQUIRED()
        
        # Build authz context
        authz_ctx = AuthzContext(
            identity=identity,
            resource=self.resource,
            action=self.permission,
            scopes=identity.scopes,
            roles=identity.roles,
            tenant_id=identity.tenant_id,
        )
        
        # Check permission
        decision = await self.authz_engine.check_permission(
            identity=identity,
            permission=self.permission,
        )
        
        from ..authz import Decision
        if decision != Decision.ALLOW:
            raise AUTHZ_POLICY_DENIED(
                policy=f"permission:{self.permission}",
                context=authz_ctx.to_dict(),
            )
        
        return context


class RequirePolicyGuard(FlowGuard):
    """
    Require custom authorization policy.
    
    Evaluates arbitrary policy function against context.
    """
    
    def __init__(
        self,
        authz_engine: AuthzEngine,
        policy_name: str,
        resource_extractor: Callable[[dict], str] | None = None,
    ):
        """
        Initialize guard.
        
        Args:
            authz_engine: Authorization engine
            policy_name: Policy name registered in ABAC engine
            resource_extractor: Function to extract resource from context
        """
        self.authz_engine = authz_engine
        self.policy_name = policy_name
        self.resource_extractor = resource_extractor
    
    async def __call__(self, context: dict[str, Any]) -> dict[str, Any]:
        """Verify policy."""
        # First verify authentication
        identity = get_identity(context)
        if not identity:
            raise AUTH_REQUIRED()
        
        # Extract resource if provided
        resource = None
        if self.resource_extractor:
            resource = self.resource_extractor(context)
        
        # Build authz context
        authz_ctx = AuthzContext(
            identity=identity,
            resource=resource,
            action=self.policy_name,
            scopes=identity.scopes,
            roles=identity.roles,
            tenant_id=identity.tenant_id,
        )
        
        # Evaluate policy
        decision = self.authz_engine.abac.evaluate(self.policy_name, authz_ctx)
        
        from ..authz import Decision
        if decision != Decision.ALLOW:
            raise AUTHZ_POLICY_DENIED(
                policy=self.policy_name,
                context=authz_ctx.to_dict(),
            )
        
        return context


# ============================================================================
# Guard Factories
# ============================================================================


def require_auth(optional: bool = False) -> FlowNode:
    """Create authentication guard node."""
    return RequireAuthGuard(optional=optional).as_flow_node(
        name="require_auth",
        priority=10,
    )


def require_scopes(*scopes: str, require_all: bool = True) -> FlowNode:
    """Create scope guard node."""
    return RequireScopesGuard(*scopes, require_all=require_all).as_flow_node(
        name=f"require_scopes:{','.join(scopes)}",
        priority=20,
    )


def require_roles(*roles: str, require_all: bool = True) -> FlowNode:
    """Create role guard node."""
    return RequireRolesGuard(*roles, require_all=require_all).as_flow_node(
        name=f"require_roles:{','.join(roles)}",
        priority=20,
    )


def require_permission(
    authz_engine: AuthzEngine,
    permission: str,
    resource: str | None = None,
) -> FlowNode:
    """Create permission guard node."""
    return RequirePermissionGuard(
        authz_engine=authz_engine,
        permission=permission,
        resource=resource,
    ).as_flow_node(
        name=f"require_permission:{permission}",
        priority=20,
    )


# ============================================================================
# Exports
# ============================================================================


__all__ = [
    # Flow helpers
    "get_session",
    "get_identity",
    "set_identity",
    # Guards
    "FlowGuard",
    "RequireAuthGuard",
    "RequireSessionAuthGuard",
    "RequireTokenAuthGuard",
    "RequireApiKeyGuard",
    "RequireScopesGuard",
    "RequireRolesGuard",
    "RequirePermissionGuard",
    "RequirePolicyGuard",
    # Factories
    "require_auth",
    "require_scopes",
    "require_roles",
    "require_permission",
]
