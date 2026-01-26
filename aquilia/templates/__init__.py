"""
AquilaTemplates - First-class Jinja2-based template rendering for Aquilia.

Production-ready, async-capable template system with:
- Manifest-driven compilation and crous artifacts
- DI-friendly Controller integration
- Sandboxed execution with security by default
- Fast precompilation, bytecode cache, streaming
- Hot-reload support in dev mode
- Observable with metrics and tracing

Example:
    from aquilia.templates import TemplateEngine, TemplateLoader
    from aquilia import Controller, GET
    
    class ProfileController(Controller):
        prefix = "/profile"
        
        def __init__(self, templates: TemplateEngine):
            self.templates = templates
        
        @GET("/")
        async def view(self, ctx):
            return await self.templates.render_to_response(
                "users/profile.html",
                {"user": ctx.identity}
            )
"""

__version__ = "1.0.0"

from .engine import TemplateEngine
from .loader import TemplateLoader, PackageLoader
from .bytecode_cache import (
    BytecodeCache,
    InMemoryBytecodeCache,
    CrousBytecodeCache,
)
from .manager import TemplateManager, TemplateLintIssue
from .middleware import TemplateMiddleware
from .context import TemplateContext, create_template_context
from .security import TemplateSandbox, SandboxPolicy
from .di_providers import (
    register_template_providers,
    create_development_engine,
    create_production_engine,
    create_testing_engine,
)
from .sessions_integration import (
    SessionTemplateProxy,
    FlashMessages,
    TemplateFlashMixin,
)
from .auth_integration import (
    IdentityTemplateProxy,
    TemplateAuthMixin,
)
from .manifest_integration import (
    discover_template_directories,
    create_manifest_aware_loader,
    ModuleTemplateRegistry,
)

__all__ = [
    # Core
    "TemplateEngine",
    "TemplateLoader",
    "PackageLoader",
    
    # Cache
    "BytecodeCache",
    "InMemoryBytecodeCache",
    "CrousBytecodeCache",
    
    # Manager
    "TemplateManager",
    "TemplateLintIssue",
    
    # Middleware
    "TemplateMiddleware",
    
    # Context
    "TemplateContext",
    "create_template_context",
    
    # Security
    "TemplateSandbox",
    "SandboxPolicy",
    
    # DI Integration
    "register_template_providers",
    "create_development_engine",
    "create_production_engine",
    "create_testing_engine",
    
    # Session Integration
    "SessionTemplateProxy",
    "FlashMessages",
    "TemplateFlashMixin",
    
    # Auth Integration
    "IdentityTemplateProxy",
    "TemplateAuthMixin",
    
    # Manifest Integration
    "discover_template_directories",
    "create_manifest_aware_loader",
    "ModuleTemplateRegistry",
]
