"""
Template Engine - Core async-capable Jinja2 template rendering engine.

Provides:
- Async rendering with streaming support
- Bytecode caching for performance
- Sandboxed execution by default
- Framework-aware context injection
- Response integration
"""

from typing import Any, AsyncIterator, Callable, Dict, Mapping, Optional, TYPE_CHECKING
import asyncio
from jinja2 import Environment, Template
from jinja2.ext import Extension

from .loader import TemplateLoader
from .bytecode_cache import BytecodeCache, InMemoryBytecodeCache
from .security import TemplateSandbox, SandboxPolicy, create_safe_filters, create_safe_globals
from .context import TemplateContext, create_template_context

if TYPE_CHECKING:
    from aquilia.response import Response
    from aquilia.controller.base import RequestCtx


class TemplateEngine:
    """
    Async-capable Jinja2 template engine.
    
    Features:
    - Sandboxed execution with security policies
    - Bytecode caching for performance
    - Async rendering and streaming
    - Framework context injection
    - Response integration
    
    Args:
        loader: Template loader
        bytecode_cache: Bytecode cache (default: in-memory)
        autoescape: Enable HTML autoescaping
        sandbox: Enable sandbox (recommended)
        sandbox_policy: Security policy for sandbox
        globals: Custom global variables/functions
        filters: Custom filters
        tests: Custom tests
        extensions: Jinja2 extensions to enable
    
    Example:
        loader = TemplateLoader(["/path/to/templates"])
        engine = TemplateEngine(loader)
        
        html = await engine.render("profile.html", {"user": user})
        response = engine.render_to_response("profile.html", {"user": user})
    """
    
    def __init__(
        self,
        loader: TemplateLoader,
        *,
        bytecode_cache: Optional[BytecodeCache] = None,
        autoescape: bool = True,
        sandbox: bool = True,
        sandbox_policy: Optional[SandboxPolicy] = None,
        globals: Optional[Dict[str, Any]] = None,
        filters: Optional[Dict[str, Callable]] = None,
        tests: Optional[Dict[str, Callable]] = None,
        extensions: Optional[list] = None,
    ):
        self.loader = loader
        self.bytecode_cache = bytecode_cache or InMemoryBytecodeCache()
        self.sandbox = sandbox
        
        # Create sandbox if enabled
        if sandbox:
            self._sandbox = TemplateSandbox(
                policy=sandbox_policy or SandboxPolicy.strict()
            )
            
            # Register custom filters
            safe_filters = create_safe_filters()
            for name, func in safe_filters.items():
                self._sandbox.register_filter(name, func)
            
            if filters:
                for name, func in filters.items():
                    self._sandbox.register_filter(name, func)
            
            # Register custom tests
            if tests:
                for name, func in tests.items():
                    self._sandbox.register_test(name, func)
            
            # Register custom globals
            safe_globals = create_safe_globals()
            for name, value in safe_globals.items():
                self._sandbox.register_global(name, value)
            
            if globals:
                for name, value in globals.items():
                    self._sandbox.register_global(name, value)
            
            # Create sandboxed environment
            self.env = self._sandbox.create_environment(
                loader=self.loader,
                bytecode_cache=self.bytecode_cache,
                extensions=extensions or [],
                enable_async=True,
            )
        else:
            # Create standard environment
            from jinja2 import Environment
            from jinja2 import select_autoescape
            
            self.env = Environment(
                loader=self.loader,
                bytecode_cache=self.bytecode_cache,
                autoescape=select_autoescape(
                    enabled_extensions=["html", "htm", "xml"],
                    default_for_string=True,
                ) if autoescape else False,
                extensions=extensions or [],
                enable_async=True,
            )
            
            # Register custom filters
            if filters:
                self.env.filters.update(filters)
            
            # Register custom tests
            if tests:
                self.env.tests.update(tests)
            
            # Register custom globals
            if globals:
                self.env.globals.update(globals)
        
        # Template cache (in addition to bytecode cache)
        self._template_cache: Dict[str, Template] = {}
        self._cache_enabled = True
    
    async def render(
        self,
        template_name: str,
        context: Optional[Mapping[str, Any]] = None,
        request_ctx: Optional["RequestCtx"] = None
    ) -> str:
        """
        Render template asynchronously.
        
        Args:
            template_name: Template name (namespace-aware)
            context: Template variables
            request_ctx: Request context (for injecting request/session/identity)
        
        Returns:
            Rendered HTML string
        
        Raises:
            TemplateNotFound: If template doesn't exist
            TemplateSyntaxError: If template has syntax errors
        """
        # Build template context
        template_context = create_template_context(
            user_context=dict(context) if context else None,
            request_ctx=request_ctx
        )
        
        # Get template
        template = self.get_template(template_name)
        
        # Render async
        rendered = await template.render_async(**template_context.to_dict())
        
        return rendered
    
    def render_sync(
        self,
        template_name: str,
        context: Optional[Mapping[str, Any]] = None,
        request_ctx: Optional["RequestCtx"] = None
    ) -> str:
        """
        Render template synchronously.
        
        Use only when async not available. Prefer async render().
        """
        # Build template context
        template_context = create_template_context(
            user_context=dict(context) if context else None,
            request_ctx=request_ctx
        )
        
        # Get template
        template = self.get_template(template_name)
        
        # Render sync
        return template.render(**template_context.to_dict())
    
    async def stream(
        self,
        template_name: str,
        context: Optional[Mapping[str, Any]] = None,
        request_ctx: Optional["RequestCtx"] = None
    ) -> AsyncIterator[bytes]:
        """
        Stream template rendering.
        
        Yields chunks of rendered content as bytes for streaming responses.
        
        Args:
            template_name: Template name
            context: Template variables
            request_ctx: Request context
        
        Yields:
            Chunks of rendered content as bytes
        """
        # Build template context
        template_context = create_template_context(
            user_context=dict(context) if context else None,
            request_ctx=request_ctx
        )
        
        # Get template
        template = self.get_template(template_name)
        
        # Generate async
        async for chunk in template.generate_async(**template_context.to_dict()):
            yield chunk.encode("utf-8")
    
    async def render_to_response(
        self,
        template_name: str,
        context: Optional[Mapping[str, Any]] = None,
        *,
        status: int = 200,
        headers: Optional[Dict[str, str]] = None,
        content_type: str = "text/html; charset=utf-8",
        request_ctx: Optional["RequestCtx"] = None
    ) -> "Response":
        """
        Render template and return Response object.
        
        Convenience method for controller integration.
        
        Args:
            template_name: Template name
            context: Template variables
            status: HTTP status code
            headers: Additional headers
            content_type: Content-Type header
            request_ctx: Request context
        
        Returns:
            Response object with rendered content
        """
        # Import here to avoid circular dependency
        from aquilia.response import Response
        
        # Render the template
        html_content = await self.render(template_name, context, request_ctx)
        
        # Create response with rendered content
        return Response(
            content=html_content,
            status=status,
            headers=headers,
            media_type=content_type
        )
    
    def template_stream_response(
        self,
        template_name: str,
        context: Optional[Mapping[str, Any]] = None,
        *,
        status: int = 200,
        headers: Optional[Dict[str, str]] = None,
        content_type: str = "text/html; charset=utf-8",
        request_ctx: Optional["RequestCtx"] = None
    ) -> "Response":
        """
        Render template as streaming response.
        
        Args:
            template_name: Template name
            context: Template variables
            status: HTTP status code
            headers: Additional headers
            content_type: Content-Type header
            request_ctx: Request context
        
        Returns:
            Response object with streaming content
        """
        from aquilia.response import Response
        
        return Response.stream(
            self.stream(template_name, context, request_ctx),
            media_type=content_type
        )
    
    def get_template(self, name: str) -> Template:
        """
        Get template by name.
        
        Uses template cache for performance.
        
        Args:
            name: Template name
        
        Returns:
            Jinja2 Template object
        """
        if self._cache_enabled and name in self._template_cache:
            return self._template_cache[name]
        
        template = self.env.get_template(name)
        
        if self._cache_enabled:
            self._template_cache[name] = template
        
        return template
    
    def invalidate_cache(self, template_name: Optional[str] = None) -> None:
        """
        Invalidate template cache.
        
        Args:
            template_name: Specific template to invalidate (None = all)
        """
        if template_name:
            self._template_cache.pop(template_name, None)
            
            # Also invalidate bytecode cache
            if hasattr(self.bytecode_cache, "invalidate"):
                self.bytecode_cache.invalidate(template_name)
        else:
            self._template_cache.clear()
            self.bytecode_cache.clear()
    
    def list_templates(self) -> list[str]:
        """
        List all available templates.
        
        Returns:
            List of template names
        """
        return self.loader.list_templates()
    
    def register_filter(self, name: str, func: Callable) -> None:
        """
        Register custom filter.
        
        Args:
            name: Filter name
            func: Filter function
        """
        if self.sandbox:
            self._sandbox.register_filter(name, func)
        self.env.filters[name] = func
    
    def register_test(self, name: str, func: Callable) -> None:
        """
        Register custom test.
        
        Args:
            name: Test name
            func: Test function
        """
        if self.sandbox:
            self._sandbox.register_test(name, func)
        self.env.tests[name] = func
    
    def register_global(self, name: str, value: Any) -> None:
        """
        Register global variable/function.
        
        Args:
            name: Global name
            value: Global value
        """
        if self.sandbox:
            self._sandbox.register_global(name, value)
        self.env.globals[name] = value
