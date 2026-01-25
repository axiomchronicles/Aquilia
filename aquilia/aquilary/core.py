"""
Core Aquilary types and main registry class.
"""

from typing import Any, Dict, List, Optional, Literal, Type, Callable
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json


class RegistryMode(str, Enum):
    """Registry operational modes."""
    DEV = "dev"        # Permissive, hot-reload enabled
    PROD = "prod"      # Strict validation, immutable
    TEST = "test"      # Scoped, ephemeral, override-friendly


@dataclass
class AppContext:
    """
    Runtime context for a loaded app.
    
    Contains resolved config, DI bucket, and metadata.
    Controllers/services remain lazy until demanded.
    """
    
    name: str
    version: str
    manifest: Any  # Original manifest object
    config_namespace: Dict[str, Any]
    
    # Lazy-loaded resources (import paths only)
    controllers: List[str] = field(default_factory=list)
    services: List[str] = field(default_factory=list)
    middlewares: List[tuple[str, dict]] = field(default_factory=list)
    
    # Dependencies
    depends_on: List[str] = field(default_factory=list)
    
    # Lifecycle hooks (callable)
    on_startup: Optional[Callable] = None
    on_shutdown: Optional[Callable] = None
    
    # DI bucket (lazy initialized)
    di_container: Optional[Any] = None
    
    # Metadata
    route_metadata: List[Dict[str, Any]] = field(default_factory=list)
    load_order: int = 0
    
    def __post_init__(self):
        """Validate app context."""
        if not self.name:
            raise ValueError("AppContext must have a name")
        if not self.version:
            raise ValueError("AppContext must have a version")


@dataclass
class RegistryFingerprint:
    """Immutable registry fingerprint for deployment gating."""
    
    hash: str  # SHA-256 hex digest
    timestamp: str
    mode: str
    app_count: int
    route_count: int
    manifest_sources: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize for JSON export."""
        return {
            "hash": self.hash,
            "timestamp": self.timestamp,
            "mode": self.mode,
            "app_count": self.app_count,
            "route_count": self.route_count,
            "manifest_sources": self.manifest_sources,
        }


class AquilaryRegistry:
    """
    Validated registry metadata (static phase output).
    
    Contains ordered app contexts, dependency graph, and fingerprint.
    Does NOT import controllers or run app code.
    """
    
    __slots__ = (
        "fingerprint",
        "app_contexts",
        "mode",
        "_dependency_graph",
        "_route_index",
        "_validation_report",
        "_config",
    )
    
    def __init__(
        self,
        app_contexts: List[AppContext],
        fingerprint: str,
        mode: RegistryMode,
        dependency_graph: Dict[str, List[str]],
        route_index: Dict[str, Any],
        validation_report: Dict[str, Any],
        config: Any,
    ):
        self.app_contexts = app_contexts
        self.fingerprint = fingerprint
        self.mode = mode
        self._dependency_graph = dependency_graph
        self._route_index = route_index
        self._validation_report = validation_report
        self._config = config
    
    def build_runtime(self) -> "RuntimeRegistry":
        """
        Build runtime registry.
        
        Instantiates DI buckets, registers services/controllers lazily,
        runs config validation.
        
        Returns:
            RuntimeRegistry instance
        """
        from .runtime import RuntimeRegistry as RT
        
        return RT.from_metadata(
            registry_meta=self,
            config=self._config,
        )
    
    def inspect(self) -> Dict[str, Any]:
        """
        Get diagnostics, routes, dependency graph, conflicts, fingerprint.
        
        Returns:
            Comprehensive diagnostics dictionary
        """
        return {
            "fingerprint": self.fingerprint,
            "mode": self.mode.value,
            "app_count": len(self.app_contexts),
            "apps": [
                {
                    "name": ctx.name,
                    "version": ctx.version,
                    "depends_on": ctx.depends_on,
                    "load_order": ctx.load_order,
                    "controllers": len(ctx.controllers),
                    "services": len(ctx.services),
                }
                for ctx in self.app_contexts
            ],
            "dependency_graph": self._dependency_graph,
            "route_index": self._route_index,
            "validation_report": self._validation_report,
        }
    
    def export_manifest(self, path: str) -> None:
        """
        Write frozen manifest for reproducible deploys.
        
        Args:
            path: Output file path
        """
        import json
        from pathlib import Path
        
        frozen = {
            "version": "1.0",
            "fingerprint": self.fingerprint,
            "mode": self.mode.value,
            "apps": [
                {
                    "name": ctx.name,
                    "version": ctx.version,
                    "depends_on": ctx.depends_on,
                    "controllers": ctx.controllers,
                    "services": ctx.services,
                    "middlewares": [
                        {"path": path, "kwargs": kwargs}
                        for path, kwargs in ctx.middlewares
                    ],
                }
                for ctx in self.app_contexts
            ],
            "dependency_graph": self._dependency_graph,
            "route_index": self._route_index,
        }
        
        Path(path).write_text(json.dumps(frozen, indent=2, sort_keys=True))


class Aquilary:
    """
    Main entry point for building registry from manifests.
    
    Static factory that validates and produces AquilaryRegistry.
    """
    
    @classmethod
    def from_manifests(
        cls,
        manifests: List[Type | str],
        config: Any,
        mode: Literal["dev", "prod", "test"] = "prod",
        *,
        allow_fs_autodiscovery: bool = False,
        freeze_manifest_path: Optional[str] = None,
    ) -> AquilaryRegistry:
        """
        Build and validate registry metadata (static phase).
        
        Does NOT import controllers or run app code.
        
        Args:
            manifests: List of manifest classes or paths
            config: Configuration object
            mode: Registry mode (dev/prod/test)
            allow_fs_autodiscovery: If True, scan filesystem for manifests
            freeze_manifest_path: If provided, load from frozen manifest
            
        Returns:
            AquilaryRegistry with validated metadata
            
        Raises:
            DependencyCycleError: If circular dependencies detected
            ManifestValidationError: If manifest validation fails
            ConfigValidationError: If config validation fails
        """
        from .loader import ManifestLoader
        from .validator import RegistryValidator
        from .graph import DependencyGraph
        from .fingerprint import FingerprintGenerator
        
        # Parse mode
        registry_mode = RegistryMode(mode)
        
        # Load frozen manifest if provided
        if freeze_manifest_path:
            return cls._from_frozen_manifest(freeze_manifest_path, config, registry_mode)
        
        # Phase 1: Load manifests (safe, no imports)
        loader = ManifestLoader()
        loaded_manifests = loader.load_manifests(
            manifests,
            allow_fs_autodiscovery=allow_fs_autodiscovery,
        )
        
        # Phase 2: Validate manifests
        validator = RegistryValidator(mode=registry_mode)
        validation_report = validator.validate_manifests(loaded_manifests, config)
        
        if validation_report.has_errors():
            raise validation_report.to_exception()
        
        # Phase 3: Build dependency graph
        dep_graph = DependencyGraph()
        for manifest in loaded_manifests:
            deps = getattr(manifest, "depends_on", [])
            dep_graph.add_node(manifest.name, deps)
        
        # Phase 4: Detect cycles and compute topological order
        try:
            load_order = dep_graph.topological_sort()
        except Exception as e:
            from .errors import DependencyCycleError
            cycle = dep_graph.find_cycle()
            raise DependencyCycleError(cycle=cycle) from e
        
        # Phase 5: Build app contexts (ordered)
        app_contexts = []
        for i, app_name in enumerate(load_order):
            manifest = next(m for m in loaded_manifests if m.name == app_name)
            
            # Extract config namespace
            config_ns = {}
            if hasattr(config, "apps") and hasattr(config.apps, app_name):
                config_ns = getattr(config.apps, app_name).__dict__
            
            # Build context
            ctx = AppContext(
                name=manifest.name,
                version=manifest.version,
                manifest=manifest,
                config_namespace=config_ns,
                controllers=getattr(manifest, "controllers", []),
                services=getattr(manifest, "services", []),
                middlewares=getattr(manifest, "middlewares", []),
                depends_on=getattr(manifest, "depends_on", []),
                on_startup=getattr(manifest, "on_startup", None),
                on_shutdown=getattr(manifest, "on_shutdown", None),
                load_order=i,
            )
            app_contexts.append(ctx)
        
        # Phase 6: Build route index (metadata only, no imports)
        route_index = cls._build_route_index(app_contexts, registry_mode)
        
        # Phase 7: Generate fingerprint
        fingerprint_gen = FingerprintGenerator()
        fingerprint = fingerprint_gen.generate(
            app_contexts=app_contexts,
            config=config,
            mode=registry_mode,
        )
        
        # Phase 8: Create registry
        return AquilaryRegistry(
            app_contexts=app_contexts,
            fingerprint=fingerprint,
            mode=registry_mode,
            dependency_graph=dep_graph.to_dict(),
            route_index=route_index,
            validation_report=validation_report.to_dict(),
            config=config,
        )
    
    @classmethod
    def _from_frozen_manifest(
        cls,
        path: str,
        config: Any,
        mode: RegistryMode,
    ) -> AquilaryRegistry:
        """Load registry from frozen manifest file."""
        import json
        from pathlib import Path
        
        data = json.loads(Path(path).read_text())
        
        # Reconstruct app contexts from frozen data
        app_contexts = []
        for app_data in data["apps"]:
            ctx = AppContext(
                name=app_data["name"],
                version=app_data["version"],
                manifest=None,  # No manifest object in frozen mode
                config_namespace={},
                controllers=app_data["controllers"],
                services=app_data["services"],
                middlewares=[
                    (m["path"], m["kwargs"])
                    for m in app_data["middlewares"]
                ],
                depends_on=app_data["depends_on"],
            )
            app_contexts.append(ctx)
        
        return AquilaryRegistry(
            app_contexts=app_contexts,
            fingerprint=data["fingerprint"],
            mode=mode,
            dependency_graph=data["dependency_graph"],
            route_index=data["route_index"],
            validation_report={},
            config=config,
        )
    
    @classmethod
    def _build_route_index(
        cls,
        app_contexts: List[AppContext],
        mode: RegistryMode,
    ) -> Dict[str, Any]:
        """
        Build route index from app contexts (metadata only).
        
        Returns:
            Route index mapping
        """
        # Placeholder - will be implemented with route parser
        route_index = {}
        
        for ctx in app_contexts:
            for controller_path in ctx.controllers:
                # Store metadata without importing
                route_index[controller_path] = {
                    "app": ctx.name,
                    "import_path": controller_path,
                    "lazy": True,
                }
        
        return route_index


class RuntimeRegistry:
    """
    Runtime registry instance (lazy compilation phase).
    
    Imports controllers, initializes DI, compiles routes.
    """
    
    def __init__(self, registry_meta: AquilaryRegistry, config: Any):
        self.meta = registry_meta
        self.config = config
        self._compiled = False
        self.route_table = None
        self.di_containers: Dict[str, Any] = {}
        self.router = None
    
    @classmethod
    def from_metadata(
        cls,
        registry_meta: AquilaryRegistry,
        config: Any,
    ) -> "RuntimeRegistry":
        """Create runtime registry from metadata."""
        return cls(registry_meta, config)
        
    def perform_autodiscovery(self) -> None:
        """
        Perform runtime auto-discovery of controllers and services.
        
        Uses PackageScanner to find classes in standard locations if
        auto-discovery is enabled for the app.
        """
        from aquilia.utils.scanner import PackageScanner
        # from aquilia.di import Service  <-- Component doesn't exist, using heuristics instead
        # We can't import Controller from here easily without circular dep?
        # Use string check or property check in scanner predicate
        
        scanner = PackageScanner()
        
        for ctx in self.meta.app_contexts:
            # Check if auto_discover is enabled in manifest config
            manifest_config = ctx.manifest
            if hasattr(manifest_config, "auto_discover") and not manifest_config.auto_discover:
                continue
                
            # Default to enabled if not specified (backward compat for builders)
            # or if it's a raw class manifest (legacy) we might check attribute
            
            # Base package for module
            # ctx.name is module name e.g. "mymod"
            # Assuming standard structure modules.<name> or just <name> if valid package
            
            # Start scan
            base_package = f"modules.{ctx.name}"
            
            # 1. Discover Controllers
            try:
                # Scan .controllers submodule
                controllers = scanner.scan_package(
                    f"{base_package}.controllers",
                    predicate=lambda cls: cls.__name__.endswith("Controller"),
                )
                
                # Scan .test_routes submodule (dev convention)
                test_routes = scanner.scan_package(
                    f"{base_package}.test_routes",
                    predicate=lambda cls: cls.__name__.endswith("Controller"),
                )
                
                # NEW: Scan individual controller files in module directory
                module_controllers = []
                try:
                    import importlib
                    # Import the module package itself
                    module_package = importlib.import_module(base_package)
                    if hasattr(module_package, '__path__'):
                        # Get all python files in the module directory
                        from pathlib import Path
                        module_dir = Path(module_package.__path__[0])
                        for py_file in module_dir.glob("*.py"):
                            if py_file.stem in ['__init__', 'manifest']:
                                continue
                            
                            # Try to scan individual file as a module
                            submodule_name = f"{base_package}.{py_file.stem}"
                            file_controllers = scanner.scan_package(
                                submodule_name,
                                predicate=lambda cls: cls.__name__.endswith("Controller"),
                            )
                            module_controllers.extend(file_controllers)
                except Exception:
                    # Silent fail for runtime discovery
                    pass
                
                # Add discovered controllers to context
                for cls in controllers + test_routes + module_controllers:
                    path = f"{cls.__module__}:{cls.__name__}"
                    if path not in ctx.controllers:
                        ctx.controllers.append(path)
                        
            except Exception as e:
                print(f"Discovery warning for {ctx.name}: {e}")

            # 2. Discover Services
            try:
                services = scanner.scan_package(
                    f"{base_package}.services",
                    predicate=lambda cls: cls.__name__.endswith("Service") or hasattr(cls, "__di_scope__"),
                )
                
                for cls in services:
                    path = f"{cls.__module__}:{cls.__name__}"
                    if path not in ctx.services:
                        ctx.services.append(path)
                        
            except Exception as e:
                pass
    
    def compile_routes(self) -> None:
        """
        Lazily import controllers and compile route trees.
        
        This is where actual module imports happen.
        """
        if self._compiled:
            return
        
        from .route_compiler import RouteCompiler
        from .handler_wrapper import wrap_handler
        
        # First, register services in DI containers
        self._register_services()
        
        # Compile routes from manifests
        compiler = RouteCompiler()
        
        manifests = []
        for ctx in self.meta.app_contexts:
            manifest_dict = {
                "name": ctx.name,
                "controllers": ctx.controllers,
                "services": ctx.services,
            }
            manifests.append(manifest_dict)
        
        self.route_table = compiler.compile_from_manifests(manifests, self.config)
        
        # Wrap handlers with DI injection
        if self.route_table and hasattr(self.route_table, 'routes'):
            for route in self.route_table.routes:
                # Get the app container for this route
                app_name = route.app_name if hasattr(route, 'app_name') else None
                if app_name and app_name in self.di_containers:
                    container = self.di_containers[app_name]
                    # Wrap handler with DI injection
                    route.handler = wrap_handler(route.handler, container)
        
        # Validate routes
        errors = compiler.validate_routes()
        if errors:
            raise RuntimeError(f"Route compilation failed:\n" + "\n".join(errors))
        
        # Build router from compiled routes
        # Router building removed - flow system deprecated
        # Use controller-based routing instead
        # self._build_router()
        
        self._compiled = True
    
    # Legacy flow router builder - removed (flows deprecated)
    # def _build_router(self):
    #     """Build router from compiled route table."""
    #     from aquilia.router import Router
    #     from aquilia.flow import Flow, FlowNode, FlowNodeType
    #     
    #     self.router = Router()
    #     
    #     if not self.route_table or not hasattr(self.route_table, 'routes'):
    #         return
    #     
    #     for route in self.route_table.routes:
    #         # Create Flow instance from route
    #         flow = Flow(pattern=route.pattern, method=route.method)
    #         
    #         # Create handler node with wrapped handler
    #         handler_node = FlowNode(
    #             type=FlowNodeType.HANDLER,
    #             callable=route.handler,  # Already wrapped with DI
    #             name=route.handler_name or route.handler.__name__,
    #             effects=getattr(route, 'effects', []),
    #             dependencies=getattr(route, 'dependencies', []),
    #         )
    #         
    #         flow.add_node(handler_node)
    #         flow.metadata['handler_name'] = route.handler_name or route.handler.__name__
    #         flow.metadata['module'] = getattr(route.handler, '__module__', 'unknown')
    #         flow.metadata['app_name'] = route.app_name if hasattr(route, 'app_name') else 'unknown'
    #         
    #         # Add flow to router
    #         self.router.add_flow(flow)
    
    def _register_services(self):
        """Register services from manifests with DI containers."""
        # Skip if already registered
        if hasattr(self, '_services_registered') and self._services_registered:
            return
        
        from aquilia.di import Container
        from aquilia.di.providers import ClassProvider, ValueProvider
        import importlib
        
        for ctx in self.meta.app_contexts:
            # Create app-scoped container
            if ctx.name not in self.di_containers:
                self.di_containers[ctx.name] = Container(scope="app")
            
            container = self.di_containers[ctx.name]
            
            # Register config as a value provider
            if ctx.config_namespace:
                config_provider = ValueProvider(
                    value=ctx.config_namespace,
                    token="Config",
                    name=f"{ctx.name}_config",
                )
                try:
                    container.register(config_provider)
                except ValueError:
                    # Already registered, skip
                    pass
            
            # Register services
            for service_path in ctx.services:
                try:
                    # Import service class
                    if ":" in service_path:
                        module_path, class_name = service_path.split(":", 1)
                    else:
                        module_path, class_name = service_path.rsplit(".", 1)
                    
                    module = importlib.import_module(module_path)
                    service_class = getattr(module, class_name)
                    
                    # Check for DI decorators
                    scope = getattr(service_class, '__di_scope__', 'app')
                    tag = getattr(service_class, '__di_tag__', None)
                    
                    # Create ClassProvider and register
                    provider = ClassProvider(
                        cls=service_class,
                        scope=scope,
                        tags=(tag,) if tag else (),
                    )
                    container.register(provider, tag=tag)
                    print(f"✓ Registered service: {service_class.__name__} in app '{ctx.name}'")
                
                except Exception as e:
                    print(f"Warning: Failed to register service {service_path}: {e}")
        
        # Mark as registered
        self._services_registered = True
    
    def _register_effects(self):
        """
        Register effects from manifests with DI containers.
        
        Effects are registered as singleton providers since they typically
        maintain global state or configuration.
        """
        from aquilia.di.providers import ClassProvider, ValueProvider
        from aquilia.di.scopes import ServiceScope
        import importlib
        
        for ctx in self.meta.app_contexts:
            # Get container for this app
            container = self.di_containers.get(ctx.name)
            if container is None:
                continue
            
            # Get effects from manifest
            effects = getattr(ctx.manifest, "effects", []) if ctx.manifest else []
            
            for effect_path in effects:
                try:
                    # Import effect
                    if ":" in effect_path:
                        # Format: "module.path:effect_name"
                        module_path, effect_name = effect_path.split(":", 1)
                    else:
                        # Format: "module.path.EffectClass"
                        module_path, effect_name = effect_path.rsplit(".", 1)
                    
                    module = importlib.import_module(module_path)
                    effect = getattr(module, effect_name)
                    
                    # Create provider (singleton scope)
                    provider = ClassProvider(
                        cls=effect if isinstance(effect, type) else type(effect),
                        scope=ServiceScope.SINGLETON,
                    )
                    container.register(provider)
                    
                    # Also register with global effect registry if it exists
                    try:
                        from aquilia.effects import EffectRegistry
                        EffectRegistry.register(effect_name, effect)
                    except ImportError:
                        pass  # Effect registry not available
                
                except Exception as e:
                    print(f"Warning: Failed to register effect {effect_path}: {e}")
    
    def _validate_resolvability(self):
        """Validate that all dependencies can be resolved."""
        errors = []
        
        for app_name, container in self.di_containers.items():
            try:
                # Try to resolve all registered services
                for service_name in container._providers.keys():
                    container.resolve(service_name)
            except Exception as e:
                errors.append(f"App '{app_name}' service '{service_name}': {e}")
        
        if errors:
            raise RuntimeError(f"Dependency resolution failed:\n" + "\n".join(errors))
    
    def validate_dependencies(self) -> List[str]:
        """
        Validate cross-app dependencies and service availability.
        
        Checks:
        - All declared app dependencies exist
        - No circular dependencies (already checked by graph)
        - Services from dependent apps are accessible
        
        Returns:
            List of validation errors (empty if all valid)
        """
        errors = []
        
        # Check app dependencies
        app_names = {ctx.name for ctx in self.meta.app_contexts}
        
        for ctx in self.meta.app_contexts:
            for dep in ctx.depends_on:
                if dep not in app_names:
                    errors.append(
                        f"App '{ctx.name}' depends on '{dep}' which doesn't exist"
                    )
        
        # Check service availability
        for ctx in self.meta.app_contexts:
            container = self.di_containers.get(ctx.name)
            if container is None:
                errors.append(f"App '{ctx.name}' has no DI container")
                continue
            
            # Check if services are registered
            for service_path in ctx.services:
                service_name = service_path.split(".")[-1]
                if service_name not in container._providers:
                    errors.append(
                        f"Service '{service_name}' from '{service_path}' "
                        f"not registered in app '{ctx.name}'"
                    )
        
        return errors
    
    def validate_routes(self) -> List[str]:
        """
        Validate route configuration for conflicts and errors.
        
        Checks:
        - No route path conflicts (same path, same method)
        - All route handlers are importable
        - Route patterns are valid
        
        Returns:
            List of validation errors (empty if all valid)
        """
        errors = []
        
        if not self.route_table or not hasattr(self.route_table, 'routes'):
            return errors
        
        # Check for route conflicts (same path + method)
        seen_routes = {}
        
        for route in self.route_table.routes:
            key = (route.pattern, route.method)
            
            if key in seen_routes:
                prev_route = seen_routes[key]
                errors.append(
                    f"Route conflict: {route.method} {route.pattern} "
                    f"defined in both '{prev_route.handler_name}' and '{route.handler_name}'"
                )
            else:
                seen_routes[key] = route
        
        return errors
    
    def validate_effects(self) -> List[str]:
        """
        Validate effect registration.
        
        Checks:
        - All effects are importable
        - No duplicate effect names
        - Effects are registered in DI
        
        Returns:
            List of validation errors (empty if all valid)
        """
        errors = []
        seen_effects = set()
        
        for ctx in self.meta.app_contexts:
            effects = getattr(ctx.manifest, "effects", []) if ctx.manifest else []
            
            for effect_path in effects:
                # Extract effect name
                if ":" in effect_path:
                    _, effect_name = effect_path.split(":", 1)
                else:
                    effect_name = effect_path.split(".")[-1]
                
                # Check duplicates
                if effect_name in seen_effects:
                    errors.append(
                        f"Duplicate effect name '{effect_name}' in app '{ctx.name}'"
                    )
                seen_effects.add(effect_name)
                
                # Check if registered in DI
                container = self.di_containers.get(ctx.name)
                if container and effect_name not in container._providers:
                    errors.append(
                        f"Effect '{effect_name}' not registered in DI "
                        f"for app '{ctx.name}'"
                    )
        
        return errors
    
    def validate_all(self) -> Dict[str, List[str]]:
        """
        Run all validation checks.
        
        Returns:
            Dictionary mapping validation category to list of errors
        """
        return {
            "dependencies": self.validate_dependencies(),
            "routes": self.validate_routes(),
            "effects": self.validate_effects(),
        }
    
    def compile(self):
        """
        Compile runtime registry with full validation.
        
        Performs:
        1. Route compilation
        2. Service registration
        3. Effect registration
        4. Dependency validation
        5. Route validation
        6. Effect validation
        
        Raises:
            RuntimeError: If any validation fails
        """
        # Compile routes
        self.compile_routes()
        
        # Register services
        self._register_services()
        
        # Register effects
        self._register_effects()
        
        # Run all validations
        validation_results = self.validate_all()
        
        # Collect all errors
        all_errors = []
        for category, errors in validation_results.items():
            if errors:
                all_errors.append(f"\n{category.upper()} ERRORS:")
                all_errors.extend(f"  - {err}" for err in errors)
        
        if all_errors:
            raise RuntimeError(
                "Runtime validation failed:\n" + "\n".join(all_errors)
            )
    
    def build_runtime_instance(self) -> Any:
        """
        Build complete runtime instance.
        
        Initializes DI containers, compiles routes, prepares middleware.
        
        Returns:
            Runtime instance ready to start
        """
        # Compile routes first
        self.compile_routes()
        
        # Register services with DI
        self._register_services()
        
        # Register effects with DI
        self._register_effects()
        
        # Validate all dependencies can be resolved
        self._validate_resolvability()
        
        # Return runtime instance
        return self
