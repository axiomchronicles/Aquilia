"""
Controller Base Class

Provides the base Controller class and RequestCtx abstraction.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from aquilia.request import Request
    from aquilia.response import Response
    from aquilia.sessions import Session
    from aquilia.auth.core import Identity


class RequestCtx:
    """
    Request context provided to controller methods.

    Uses manual __init__ instead of @dataclass for faster construction.
    No __slots__ to allow dynamic attribute setting by middleware/plugins.
    """

    def __init__(
        self,
        request: "Request",
        identity: Optional["Identity"] = None,
        session: Optional["Session"] = None,
        container: Optional[Any] = None,
        state: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ):
        self.request = request
        self.identity = identity
        self.session = session
        self.container = container
        self.state = state if state is not None else {}
        self.request_id = request_id
    
    @property
    def path(self) -> str:
        """Request path."""
        return self.request.path
    
    @property
    def method(self) -> str:
        """Request method."""
        return self.request.method
    
    @property
    def headers(self) -> Dict[str, str]:
        """Request headers."""
        return self.request.headers
    
    @property
    def query_params(self) -> Dict[str, list]:
        """Query parameters (parsed from query string)."""
        return self.request.query_params
    
    def query_param(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get single query parameter."""
        return self.request.query_param(key, default)
    
    async def json(self) -> Any:
        """Parse request body as JSON."""
        return await self.request.json()
    
    async def form(self) -> Dict[str, Any]:
        """Parse request body as form data."""
        return await self.request.form()


class Controller:
    """
    Base Controller class.
    
    Controllers are class-based request handlers with:
    - Constructor DI injection
    - Method-level route definitions
    - Class-level and method-level pipelines
    - Lifecycle hooks
    - Template rendering support
    
    Class Attributes:
        prefix: URL prefix for all routes (e.g., "/users")
        pipeline: List of pipeline nodes applied to all methods
        tags: OpenAPI tags
        instantiation_mode: "per_request" or "singleton"
    
    Lifecycle Hooks:
        async def on_startup(self, ctx): Called at app startup (singleton only)
        async def on_shutdown(self, ctx): Called at app shutdown (singleton only)
        async def on_request(self, ctx): Called before each request
        async def on_response(self, ctx, response): Called after each request
    
    Example:
        class UsersController(Controller):
            prefix = "/users"
            pipeline = [Auth.guard()]
            
            def __init__(self, repo: UserRepo, templates: TemplateEngine):
                self.repo = repo
                self.templates = templates
            
            @GET("/")
            async def list(self, ctx):
                users = self.repo.list_all()
                return self.render("users/list.html", {"users": users}, ctx)
    """
    
    # Class-level configuration
    prefix: str = ""
    pipeline: List[Any] = []
    tags: List[str] = []
    instantiation_mode: str = "per_request"  # or "singleton"
    
    # Template engine (injected via DI)
    _template_engine: Optional[Any] = None
    
    async def render(
        self,
        template_name: str,
        context: Optional[Dict[str, Any]] = None,
        request_ctx: Optional[RequestCtx] = None,
        *,
        engine: Optional[Any] = None,
        status: int = 200,
        headers: Optional[Dict[str, str]] = None
    ) -> "Response":
        """
        Render template and return Response.
        
        Convenience method for template rendering in controllers.
        Automatically injects request context if available.
        
        Args:
            template_name: Template name
            context: Template variables
            request_ctx: Request context (auto-injects request/session/identity)
            engine: Template engine (optional, can be injected or passed)
            status: HTTP status code
            headers: Additional headers
        
        Returns:
            Response with rendered template
        
        Example:
            @GET("/profile")
            async def profile(self, ctx):
                user = await self.repo.get(ctx.identity.id)
                return await self.render("profile.html", {"user": user}, ctx)
        """
        from aquilia.response import Response
        
        # Get template engine (if not provided as parameter)
        if engine is None:
            engine = getattr(self, "_template_engine", None) or getattr(self, "templates", None)
        
        return await Response.render(
            template_name,
            context,
            status=status,
            headers=headers,
            engine=engine,
            request_ctx=request_ctx
        )
    
    # Lifecycle hooks (optional)
    
    async def on_startup(self, ctx: RequestCtx) -> None:
        """
        Called when controller is initialized (singleton mode only).
        
        Use for one-time initialization like opening DB connections.
        """
        pass
    
    async def on_shutdown(self, ctx: RequestCtx) -> None:
        """
        Called when controller is destroyed (singleton mode only).
        
        Use for cleanup like closing connections.
        """
        pass
    
    async def on_request(self, ctx: RequestCtx) -> None:
        """
        Called before each request is processed.
        
        Use for per-request initialization or validation.
        """
        pass
    
    async def on_response(self, ctx: RequestCtx, response: "Response") -> "Response":
        """
        Called after each request is processed.
        
        Can modify the response before it's sent.
        
        Args:
            ctx: Request context
            response: The response to be sent
        
        Returns:
            Modified response
        """
        return response
    
    # Context manager support for per-request lifecycle
    
    async def __aenter__(self):
        """Enter request context (per-request mode)."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit request context (per-request mode)."""
        pass
