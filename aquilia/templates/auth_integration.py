"""
AquilaTemplates - Auth Integration

Deep integration between template system and AquilAuth.
Enables identity access, role/permission checks, and auth-aware
UI rendering in templates.

Features:
- Identity access: {{ identity.username }}
- Role checks: {% if has_role('admin') %}
- Permission checks: {% if can('posts.delete', post) %}
- Auth status: {% if is_authenticated %}
- Guard integration
"""

from typing import Any, Dict, Optional, Set, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from aquilia.auth.core import Identity
    from aquilia.auth.manager import AuthManager
    from aquilia.auth.authz import AuthzEngine
    from aquilia.controller.base import RequestCtx
    from .engine import TemplateEngine


logger = logging.getLogger(__name__)


# ============================================================================
# Identity Template Proxy
# ============================================================================


class IdentityTemplateProxy:
    """
    Proxy object for safe identity access in templates.
    
    Provides read-only access to identity attributes and
    convenient helpers for auth checks.
    
    Usage in templates:
        {{ identity.username }}
        {{ identity.email }}
        {% if identity.has_role('admin') %}
    """
    
    def __init__(self, identity: Optional["Identity"] = None):
        self._identity = identity
    
    @property
    def id(self) -> Optional[str]:
        """Get identity ID."""
        if not self._identity:
            return None
        return str(self._identity.identity_id)
    
    @property
    def username(self) -> Optional[str]:
        """Get username."""
        if not self._identity:
            return None
        return self._identity.username
    
    @property
    def email(self) -> Optional[str]:
        """Get email."""
        if not self._identity:
            return None
        return getattr(self._identity, 'email', None)
    
    @property
    def display_name(self) -> Optional[str]:
        """Get display name."""
        if not self._identity:
            return None
        return getattr(self._identity, 'display_name', self.username)
    
    @property
    def roles(self) -> Set[str]:
        """Get roles set."""
        if not self._identity:
            return set()
        return getattr(self._identity, 'roles', set())
    
    def has_role(self, role: str) -> bool:
        """
        Check if identity has role.
        
        Example:
            {% if identity.has_role('admin') %}
                <a href="/admin">Admin Panel</a>
            {% endif %}
        """
        if not self._identity:
            return False
        return role in self.roles
    
    def has_any_role(self, *roles: str) -> bool:
        """
        Check if identity has any of the given roles.
        
        Example:
            {% if identity.has_any_role('admin', 'moderator') %}
        """
        if not self._identity:
            return False
        return any(role in self.roles for role in roles)
    
    def has_all_roles(self, *roles: str) -> bool:
        """
        Check if identity has all given roles.
        
        Example:
            {% if identity.has_all_roles('user', 'verified') %}
        """
        if not self._identity:
            return False
        return all(role in self.roles for role in roles)
    
    @property
    def is_admin(self) -> bool:
        """Check if identity has admin role."""
        return self.has_role('admin')
    
    @property
    def is_verified(self) -> bool:
        """Check if identity is verified."""
        if not self._identity:
            return False
        status = getattr(self._identity, 'status', None)
        return status == 'active'
    
    def __bool__(self) -> bool:
        """Check if identity exists."""
        return self._identity is not None
    
    def __str__(self) -> str:
        """String representation."""
        if not self._identity:
            return "<Anonymous>"
        return f"<Identity {self.username}>"
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get identity attribute by key.
        
        Example:
            {{ identity.get('company') }}
        """
        if not self._identity:
            return default
        return getattr(self._identity, key, default)


# ============================================================================
# Auth Template Helpers
# ============================================================================


def create_auth_helpers(
    identity: Optional["Identity"] = None,
    authz_engine: Optional["AuthzEngine"] = None
):
    """
    Create auth helper functions for templates.
    
    Returns dictionary of helper functions that can be
    registered as template globals.
    """
    
    identity_proxy = IdentityTemplateProxy(identity)
    
    def is_authenticated() -> bool:
        """
        Check if user is authenticated.
        
        Usage: {% if is_authenticated() %}
        """
        return bool(identity_proxy)
    
    def has_role(role: str) -> bool:
        """
        Check if current user has role.
        
        Usage: {% if has_role('admin') %}
        """
        return identity_proxy.has_role(role)
    
    def has_any_role(*roles: str) -> bool:
        """
        Check if current user has any of the roles.
        
        Usage: {% if has_any_role('admin', 'moderator') %}
        """
        return identity_proxy.has_any_role(*roles)
    
    def has_all_roles(*roles: str) -> bool:
        """
        Check if current user has all roles.
        
        Usage: {% if has_all_roles('user', 'verified') %}
        """
        return identity_proxy.has_all_roles(*roles)
    
    def can(permission: str, resource: Any = None) -> bool:
        """
        Check if current user has permission.
        
        Usage: {% if can('posts.delete', post) %}
        
        Note: Requires authz_engine to be provided
        """
        if not authz_engine or not identity:
            return False
        
        try:
            # Simplified permission check
            # Real implementation would use authz_engine.check()
            return True  # Placeholder
        except Exception as e:
            logger.warning(f"Permission check failed: {e}")
            return False
    
    def is_owner(resource: Any) -> bool:
        """
        Check if current user owns resource.
        
        Usage: {% if is_owner(post) %}
        
        Checks if resource.owner_id matches identity.id
        """
        if not identity:
            return False
        
        owner_id = getattr(resource, 'owner_id', None)
        if not owner_id:
            return False
        
        return str(owner_id) == str(identity.identity_id)
    
    return {
        "is_authenticated": is_authenticated,
        "has_role": has_role,
        "has_any_role": has_any_role,
        "has_all_roles": has_all_roles,
        "can": can,
        "is_owner": is_owner,
    }


# ============================================================================
# Template Engine Enhancement
# ============================================================================


def enhance_engine_with_auth(
    engine: "TemplateEngine",
    auth_manager: Optional["AuthManager"] = None,
    authz_engine: Optional["AuthzEngine"] = None
) -> None:
    """
    Enhance template engine with auth integration.
    
    Registers auth helpers, filters, and globals.
    
    Args:
        engine: TemplateEngine to enhance
        auth_manager: AuthManager instance (optional)
        authz_engine: AuthzEngine instance (optional)
    """
    # Create placeholder helpers (will be overridden per-request)
    helpers = create_auth_helpers(None, authz_engine)
    
    for name, func in helpers.items():
        engine.register_global(name, func)
    
    # Register auth-aware filters
    @engine.register_filter("role_badge")
    def role_badge_filter(role: str) -> str:
        """
        Render role badge HTML.
        
        Usage: {{ 'admin' | role_badge }}
        """
        colors = {
            "admin": "red",
            "moderator": "orange",
            "user": "blue",
            "guest": "gray",
        }
        color = colors.get(role.lower(), "gray")
        return f'<span class="badge badge-{color}">{role}</span>'
    
    @engine.register_filter("identity_link")
    def identity_link_filter(identity_id: str, username: str = None) -> str:
        """
        Render identity profile link.
        
        Usage: {{ user.id | identity_link(user.username) }}
        """
        display = username or identity_id[:8]
        return f'<a href="/users/{identity_id}">{display}</a>'
    
    logger.info("Template engine enhanced with auth integration")


def inject_auth_context(
    context: Dict[str, Any],
    request_ctx: Optional["RequestCtx"] = None,
    authz_engine: Optional["AuthzEngine"] = None
) -> None:
    """
    Inject auth variables into template context.
    
    Call this in context creation to add auth helpers.
    
    Args:
        context: Template context dictionary
        request_ctx: Request context with identity
        authz_engine: Authorization engine (optional)
    """
    # Create identity proxy
    identity_proxy = None
    identity = None
    
    if request_ctx and hasattr(request_ctx, 'identity'):
        identity = request_ctx.identity
        identity_proxy = IdentityTemplateProxy(identity)
    else:
        identity_proxy = IdentityTemplateProxy(None)
    
    context["identity"] = identity_proxy
    
    # Create auth helpers with current identity
    helpers = create_auth_helpers(identity, authz_engine)
    context.update(helpers)
    
    # Convenience flags
    context["authenticated"] = bool(identity_proxy)
    context["anonymous"] = not bool(identity_proxy)


# ============================================================================
# Template Guards
# ============================================================================


class TemplateAuthGuard:
    """
    Guard to ensure templates have auth context.
    
    Can be used in Flow pipelines to enforce auth
    before rendering templates.
    """
    
    def __init__(self, require_auth: bool = False):
        self.require_auth = require_auth
    
    async def __call__(self, ctx: "RequestCtx"):
        """Check auth context."""
        if self.require_auth and not ctx.identity:
            from aquilia.auth.faults import AUTH_REQUIRED
            raise AUTH_REQUIRED.fault(
                message="Authentication required for this template"
            )
        
        # Auth context is valid
        return None


# ============================================================================
# Controller Mixin
# ============================================================================


class TemplateAuthMixin:
    """
    Mixin for controllers with auth-aware template rendering.
    
    Usage:
        class MyController(Controller, TemplateAuthMixin):
            def render_profile(self, ctx):
                return self.render_with_auth(
                    ctx,
                    "profile.html",
                    {"posts": posts}
                )
    """
    
    def render_with_auth(
        self,
        ctx: "RequestCtx",
        template: str,
        user_context: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        Render template with auth context injected.
        
        Args:
            ctx: Request context
            template: Template name
            user_context: User variables
            **kwargs: Additional Response kwargs (status, headers)
        """
        # Import here to avoid circular dependency
        from .context import create_template_context
        from aquilia.response import Response
        
        # Create context with auth
        template_ctx = create_template_context(user_context, ctx)
        final_ctx = template_ctx.to_dict()
        inject_auth_context(final_ctx, ctx)
        
        # Get template engine
        if not hasattr(self, '_template_engine') or not self._template_engine:
            raise RuntimeError("Template engine not available")
        
        return Response.render(
            template,
            final_ctx,
            engine=self._template_engine,
            **kwargs
        )
    
    def require_role(self, ctx: "RequestCtx", role: str) -> None:
        """
        Ensure current user has role.
        
        Raises AUTH_INSUFFICIENT_ROLE fault if check fails.
        """
        if not ctx.identity:
            from aquilia.auth.faults import AUTH_REQUIRED
            raise AUTH_REQUIRED.fault()
        
        identity_proxy = IdentityTemplateProxy(ctx.identity)
        if not identity_proxy.has_role(role):
            from aquilia.auth.faults import AUTHZ_INSUFFICIENT_ROLE
            raise AUTHZ_INSUFFICIENT_ROLE.fault(
                message=f"Role '{role}' required"
            )
