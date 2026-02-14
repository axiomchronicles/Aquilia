"""
Template Context - Context building and injection helpers.

Provides utilities for creating template rendering contexts with
request, session, identity, and framework globals.
"""

from typing import Any, Dict, Optional, TYPE_CHECKING
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from aquilia.request import Request
    from aquilia.sessions import Session
    from aquilia.auth.core import Identity
    from aquilia.controller.base import RequestCtx


@dataclass
class TemplateContext:
    """
    Template rendering context.
    
    Wraps user-provided context with framework-injected globals.
    
    Attributes:
        user_context: User-provided template variables
        request: Current HTTP request
        session: Active session (if available)
        identity: Authenticated identity (if available)
        extras: Additional framework-injected variables
    """
    
    user_context: Dict[str, Any] = field(default_factory=dict)
    request: Optional["Request"] = None
    session: Optional["Session"] = None
    identity: Optional["Identity"] = None
    extras: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to flat dictionary for Jinja2 rendering.
        
        Merges user context with framework variables.
        Priority: user_context > extras > framework vars
        """
        context = {}
        
        # Framework variables (lowest priority)
        if self.request is not None:
            context["request"] = self.request
        
        if self.session is not None:
            context["session"] = self.session
        
        if self.identity is not None:
            context["identity"] = self.identity
        
        # Extras (medium priority)
        context.update(self.extras)
        
        # User context (highest priority)
        context.update(self.user_context)
        
        return context


def create_template_context(
    user_context: Optional[Dict[str, Any]] = None,
    request_ctx: Optional["RequestCtx"] = None,
    **extras
) -> TemplateContext:
    """
    Create template context from request context and user variables.
    
    Automatically injects session and auth helpers when available.
    
    Args:
        user_context: User-provided template variables
        request_ctx: Request context (from controller)
        **extras: Additional variables to inject
    
    Returns:
        TemplateContext ready for rendering
    """
    ctx = TemplateContext(
        user_context=user_context or {},
        extras=extras
    )
    
    if request_ctx:
        ctx.request = request_ctx.request
        ctx.session = request_ctx.session
        ctx.identity = request_ctx.identity
        
        # Deep integration: Inject session helpers
        try:
            from .sessions_integration import inject_session_context
            final_ctx = ctx.to_dict()
            inject_session_context(final_ctx, request_ctx)
            # Update extras with session helpers
            for key, value in final_ctx.items():
                if key not in ctx.user_context:
                    ctx.extras[key] = value
        except ImportError:
            pass  # Sessions integration not available
        
        # Deep integration: Inject auth helpers
        try:
            from .auth_integration import inject_auth_context
            final_ctx = ctx.to_dict()
            inject_auth_context(final_ctx, request_ctx)
            # Update extras with auth helpers
            for key, value in final_ctx.items():
                if key not in ctx.user_context:
                    ctx.extras[key] = value
        except ImportError:
            pass  # Auth integration not available
        
        # Inject helpers from request.state (set by TemplateMiddleware)
        if hasattr(ctx.request, "state"):
            state = ctx.request.state
            if "template_url_for" in state:
                inject_url_helpers(ctx.extras, state["template_url_for"])
            if "template_static" in state:
                inject_static_helper(ctx.extras, state["template_static"])
            if "template_config" in state:
                inject_config(ctx.extras, state["template_config"])
            if "template_csrf_token" in state:
                inject_csrf_token(ctx.extras, state["template_csrf_token"])
            if "csp_nonce" in state:
                inject_csp_nonce(ctx.extras, state["csp_nonce"])
    
    return ctx


def inject_url_helpers(context: Dict[str, Any], url_for_func: Any) -> None:
    """
    Inject URL generation helpers into context.
    
    Args:
        context: Template context dictionary
        url_for_func: URL generation function
    """
    context["url_for"] = url_for_func
    
    # Static URL helper (legacy fallback — prefer inject_static_helper)
    if "static" not in context:
        def static_url(path: str) -> str:
            """Generate static asset URL."""
            return f"/static/{path.lstrip('/')}"
        
        context["static_url"] = static_url
        context["static"] = static_url


def inject_static_helper(context: Dict[str, Any], static_func: Any) -> None:
    """
    Inject static asset URL helper into context.

    Available in templates as:
        {{ static('css/app.css') }}
        {{ static('js/main.js') }}

    This is the Aquilia equivalent of Django's {% static %} tag.

    Args:
        context: Template context dictionary
        static_func: Function that takes a path and returns a URL
    """
    context["static"] = static_func
    context["static_url"] = static_func


def inject_csp_nonce(context: Dict[str, Any], nonce: str) -> None:
    """
    Inject CSP nonce into context.

    Available in templates as:
        <script nonce="{{ csp_nonce }}">...</script>
        <style nonce="{{ csp_nonce }}">...</style>

    Args:
        context: Template context dictionary
        nonce: Per-request CSP nonce string
    """
    context["csp_nonce"] = nonce


def inject_csrf_token(context: Dict[str, Any], token: Optional[str] = None) -> None:
    """
    Inject CSRF token into context.
    
    Args:
        context: Template context dictionary
        token: CSRF token (if available)
    """
    if token:
        context["csrf_token"] = token
    else:
        context["csrf_token"] = ""


def inject_config(context: Dict[str, Any], config: Any) -> None:
    """
    Inject safe config subset into context.
    
    Args:
        context: Template context dictionary
        config: Application config object
    """
    # Only expose safe, non-sensitive config values
    safe_config = {
        "debug": getattr(config, "debug", False),
        "app_name": getattr(config, "app_name", "Aquilia"),
    }
    
    context["config"] = safe_config


def inject_i18n(context: Dict[str, Any], gettext_func: Any = None) -> None:
    """
    Inject internationalization helpers into context.
    
    Args:
        context: Template context dictionary
        gettext_func: gettext function (if i18n enabled)
    """
    if gettext_func:
        context["_"] = gettext_func
        context["gettext"] = gettext_func
    else:
        # Fallback passthrough
        context["_"] = lambda s: s
        context["gettext"] = lambda s: s
