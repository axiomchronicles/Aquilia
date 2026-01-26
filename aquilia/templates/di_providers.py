"""
AquilaTemplates - DI Providers

Dependency injection providers for template engine components.
Enables automatic registration and lifecycle management.

This module provides:
- TemplateEngine provider with auto-configuration
- TemplateLoader provider with module-aware paths
- BytecodeCache provider selection
- TemplateSandbox provider with security policies
- Integration with manifest for auto-discovery
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, List, Optional

from aquilia.di.decorators import service, factory
from aquilia.config import Config

from .engine import TemplateEngine
from .loader import TemplateLoader
from .bytecode_cache import (
    BytecodeCache,
    InMemoryBytecodeCache,
    CrousBytecodeCache,
)
from .security import TemplateSandbox, SandboxPolicy
from .manager import TemplateManager

if TYPE_CHECKING:
    from aquilia.sessions import SessionEngine
    from aquilia.auth.manager import AuthManager
    from aquilia.faults import FaultEngine


logger = logging.getLogger(__name__)


# ============================================================================
# Template Component Providers
# ============================================================================


@service(scope="app")
class TemplateLoaderProvider:
    """Provider for TemplateLoader with auto-discovered paths."""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config
    
    def provide(self) -> TemplateLoader:
        """Provide TemplateLoader with configured search paths."""
        search_paths = self._discover_template_paths()
        
        logger.info(
            f"TemplateLoader initialized with {len(search_paths)} search paths"
        )
        
        return TemplateLoader(search_paths=search_paths)
    
    def _discover_template_paths(self) -> List[Path]:
        """
        Discover template directories from:
        1. Config: templates.search_paths
        2. Manifest: module.aq templates: section
        3. Convention: {module}/templates/
        4. Default: ./templates/
        """
        paths = []
        
        # From config
        if self.config:
            config_paths = self.config.get("templates.search_paths", [])
            for path_str in config_paths:
                path = Path(path_str)
                if path.exists():
                    paths.append(path)
        
        # From manifest auto-discovery
        try:
            from .manifest_integration import discover_template_directories
            manifest_paths = discover_template_directories(
                root_path=Path.cwd(),
                scan_manifests=True
            )
            paths.extend(manifest_paths)
        except ImportError:
            logger.debug("Manifest integration not available")
        
        # Deduplicate
        unique_paths = list(set(paths))
        
        return unique_paths or [Path.cwd() / "templates"]  # Default fallback


@service(scope="app")
class BytecodeCacheProvider:
    """Provider for bytecode cache with strategy selection."""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config
    
    def provide(self) -> BytecodeCache:
        """
        Provide bytecode cache based on config:
        - templates.cache: "memory", "crous", "redis", "none"
        """
        if not self.config:
            return InMemoryBytecodeCache(max_size=100)
        
        cache_type = self.config.get("templates.cache", "memory")
        
        if cache_type == "memory":
            max_size = self.config.get("templates.cache_size", 100)
            return InMemoryBytecodeCache(max_size=max_size)
        
        elif cache_type == "crous":
            # Crous bytecode cache for persistent compilation
            return CrousBytecodeCache()
        
        elif cache_type == "none":
            # No caching (development mode)
            return None
        
        else:
            logger.warning(
                f"Unknown cache type '{cache_type}', using in-memory cache"
            )
            return InMemoryBytecodeCache(max_size=100)


@service(scope="app")
class TemplateSandboxProvider:
    """Provider for template sandbox with security policies."""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config
    
    def provide(self) -> Optional[TemplateSandbox]:
        """
        Provide sandbox based on config:
        - templates.sandbox: true/false
        - templates.sandbox_policy: "strict", "permissive"
        """
        if not self.config:
            # Default: strict sandbox in production
            return TemplateSandbox(policy=SandboxPolicy.STRICT)
        
        sandbox_enabled = self.config.get("templates.sandbox", True)
        if not sandbox_enabled:
            return None
        
        policy_name = self.config.get("templates.sandbox_policy", "strict")
        policy = (
            SandboxPolicy.STRICT
            if policy_name == "strict"
            else SandboxPolicy.PERMISSIVE
        )
        
        return TemplateSandbox(policy=policy)


@service(scope="app")
class TemplateEngineProvider:
    """
    Provider for TemplateEngine with full DI integration.
    
    Automatically wires:
    - TemplateLoader (with auto-discovered paths)
    - BytecodeCache (configured strategy)
    - TemplateSandbox (security policies)
    - SessionEngine integration (for session access in templates)
    - AuthManager integration (for auth helpers in templates)
    """
    
    def __init__(
        self,
        loader: TemplateLoader,
        bytecode_cache: Optional[BytecodeCache] = None,
        sandbox: Optional[TemplateSandbox] = None,
        session_engine: Optional["SessionEngine"] = None,
        auth_manager: Optional["AuthManager"] = None,
        config: Optional[Config] = None,
    ):
        self.loader = loader
        self.bytecode_cache = bytecode_cache
        self.sandbox = sandbox
        self.session_engine = session_engine
        self.auth_manager = auth_manager
        self.config = config
    
    def provide(self) -> TemplateEngine:
        """Provide fully configured TemplateEngine."""
        # Create engine
        engine = TemplateEngine(
            loader=self.loader,
            bytecode_cache=self.bytecode_cache,
            sandbox=self.sandbox,
        )
        
        # Register session helpers if available
        if self.session_engine:
            self._register_session_helpers(engine)
        
        # Register auth helpers if available
        if self.auth_manager:
            self._register_auth_helpers(engine)
        
        # Register config access
        if self.config:
            engine.register_global("config", self.config)
        
        logger.info(
            f"TemplateEngine initialized (sandbox={bool(self.sandbox)}, "
            f"cache={type(self.bytecode_cache).__name__})"
        )
        
        return engine
    
    def _register_session_helpers(self, engine: TemplateEngine) -> None:
        """Register session access helpers in templates."""
        # Global function to access session
        def get_session():
            """Get current session from request context."""
            # This will be enhanced with proper request context access
            # For now, it's a placeholder for deep integration
            return None
        
        engine.register_global("session", get_session)
        logger.debug("Registered session helpers in templates")
    
    def _register_auth_helpers(self, engine: TemplateEngine) -> None:
        """Register auth/identity helpers in templates."""
        # Helper to check if user is authenticated
        def is_authenticated() -> bool:
            """Check if current user is authenticated."""
            # This will be enhanced with proper request context access
            return False
        
        # Helper to check roles
        def has_role(role: str) -> bool:
            """Check if current user has role."""
            return False
        
        # Helper to check permissions
        def has_permission(permission: str) -> bool:
            """Check if current user has permission."""
            return False
        
        engine.register_global("is_authenticated", is_authenticated)
        engine.register_global("has_role", has_role)
        engine.register_global("has_permission", has_permission)
        
        logger.debug("Registered auth helpers in templates")


@service(scope="app")
class TemplateManagerProvider:
    """Provider for TemplateManager (compile/lint/inspect tools)."""
    
    def __init__(self, engine: TemplateEngine):
        self.engine = engine
    
    def provide(self) -> TemplateManager:
        """Provide TemplateManager instance."""
        return TemplateManager(engine=self.engine)


# ============================================================================
# Auto-Registration Function
# ============================================================================


def register_template_providers(container) -> None:
    """
    Register all template providers with DI container.
    
    Call this during app initialization to enable automatic
    TemplateEngine injection in controllers.
    
    Example:
        from aquilia.templates.di_providers import register_template_providers
        
        container = Container()
        register_template_providers(container)
    """
    # Register in dependency order
    container.register_provider(TemplateLoaderProvider)
    container.register_provider(BytecodeCacheProvider)
    container.register_provider(TemplateSandboxProvider)
    container.register_provider(TemplateEngineProvider)
    container.register_provider(TemplateManagerProvider)
    
    logger.info("AquilaTemplates providers registered with DI container")


# ============================================================================
# Factory Functions for Common Configurations
# ============================================================================


@factory(scope="app")
def create_development_engine(
    loader: TemplateLoader,
    config: Optional[Config] = None,
) -> TemplateEngine:
    """
    Factory for development template engine:
    - No bytecode cache (always reload)
    - Permissive sandbox
    - Debug mode enabled
    """
    sandbox = TemplateSandbox(policy=SandboxPolicy.PERMISSIVE)
    
    engine = TemplateEngine(
        loader=loader,
        bytecode_cache=None,  # No cache in dev
        sandbox=sandbox,
    )
    
    logger.info("Development TemplateEngine created")
    return engine


@factory(scope="app")
def create_production_engine(
    loader: TemplateLoader,
    bytecode_cache: BytecodeCache,
    config: Optional[Config] = None,
) -> TemplateEngine:
    """
    Factory for production template engine:
    - Crous bytecode cache (persistent)
    - Strict sandbox
    - Optimized for performance
    """
    sandbox = TemplateSandbox(policy=SandboxPolicy.STRICT)
    
    engine = TemplateEngine(
        loader=loader,
        bytecode_cache=bytecode_cache,
        sandbox=sandbox,
    )
    
    logger.info("Production TemplateEngine created")
    return engine


@factory(scope="transient")
def create_testing_engine(
    search_paths: Optional[List[Path]] = None,
) -> TemplateEngine:
    """
    Factory for testing template engine:
    - In-memory cache
    - No sandbox (for testing flexibility)
    - Simple configuration
    """
    if not search_paths:
        search_paths = [Path.cwd() / "tests" / "templates"]
    
    loader = TemplateLoader(search_paths=search_paths)
    cache = InMemoryBytecodeCache(max_size=50)
    
    engine = TemplateEngine(
        loader=loader,
        bytecode_cache=cache,
        sandbox=None,  # No sandbox in tests
    )
    
    logger.info("Testing TemplateEngine created")
    return engine
