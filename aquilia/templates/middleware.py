"""
Template Middleware - Automatic context injection for templates.

Injects common variables into template context:
- request: Current HTTP request
- session: Active session (if available)
- identity: Authenticated identity (if available)
- url_for: URL generation helper
- static: Static asset URL generator (like Django's {% static %})
- csrf_token: CSRF token (if available)
- config: Safe config subset
- csp_nonce: CSP nonce (if CSPMiddleware is active)
"""

from typing import Any, Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from aquilia.request import Request
    from aquilia.response import Response
    from aquilia.di import RequestCtx
    from aquilia.middleware import Handler


class TemplateMiddleware:
    """
    Template context injection middleware.
    
    Automatically injects framework variables into template context
    for all rendered responses.
    
    Injected variables:
    - request: HTTP request object
    - session: Session object (if sessions enabled)
    - identity: Authenticated user (if auth successful)
    - url_for: URL generation function
    - static: Static asset URL function (prefix-aware)
    - csrf_token: CSRF token string
    - config: Safe config values
    - csp_nonce: Per-request CSP nonce (if CSPMiddleware is active)
    
    Args:
        url_for: URL generation function
        config: Application config
        csrf_token_func: Function to get CSRF token from request
        static_url_prefix: URL prefix for static files (default "/static")
        static_url_func: Custom function for static URL generation
    
    Example:
        middleware = TemplateMiddleware(
            url_for=router.url_for,
            config=app_config
        )
        app.add_middleware(middleware)
    """
    
    def __init__(
        self,
        url_for: Optional[Callable] = None,
        config: Optional[Any] = None,
        csrf_token_func: Optional[Callable] = None,
        static_url_prefix: str = "/static",
        static_url_func: Optional[Callable] = None,
    ):
        self.url_for = url_for or self._default_url_for
        self.config = config
        self.csrf_token_func = csrf_token_func
        self._static_prefix = static_url_prefix.rstrip("/")
        self._static_url_func = static_url_func
    
    async def __call__(
        self,
        request: "Request",
        ctx: "RequestCtx",
        next_handler: "Handler"
    ) -> "Response":
        """
        Process request and inject template context.
        
        Args:
            request: HTTP request
            ctx: Request context (DI container)
            next_handler: Next middleware/handler
        
        Returns:
            Response from handler
        """
        # Store middleware data in request state for template engine to access
        if not hasattr(request, "state"):
            request.state = {}
        
        # Inject helpers
        request.state["template_url_for"] = self.url_for
        request.state["template_config"] = self._get_safe_config()
        
        # Static URL function — available as {{ static('css/app.css') }} in templates
        if self._static_url_func:
            request.state["template_static"] = self._static_url_func
        else:
            prefix = self._static_prefix
            request.state["template_static"] = lambda path: f"{prefix}/{path.lstrip('/')}"
        
        if self.csrf_token_func:
            request.state["template_csrf_token"] = self.csrf_token_func(request)
        
        # Call next middleware/handler
        response = await next_handler(request, ctx)
        
        return response
    
    def _default_url_for(self, name: str, **params) -> str:
        """Default URL generation (placeholder)."""
        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"/{name}"
        if query:
            url += f"?{query}"
        return url
    
    def _get_safe_config(self) -> dict:
        """Get safe config subset for templates."""
        if not self.config:
            return {}
        
        # Only expose safe, non-sensitive values
        safe_config = {}
        
        # Allowlist of safe config keys
        safe_keys = ["debug", "app_name", "environment"]
        
        for key in safe_keys:
            if hasattr(self.config, key):
                safe_config[key] = getattr(self.config, key)
        
        return safe_config
