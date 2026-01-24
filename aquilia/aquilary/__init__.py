"""
Aquilary - Manifest-driven App Registry for Aquilia

Production-grade registry system that:
- Safely discovers and validates manifests (no import-time side effects)
- Builds deterministic app loading order (dependency-aware)
- Produces scoped runtime registries with fingerprints
- Integrates with DI/effects/router/middleware
- Supports dev hot-reload and freeze mode for deploys
"""

__version__ = "1.0.0"

from .core import (
    Aquilary,
    AquilaryRegistry,
    RuntimeRegistry,
    AppContext,
    RegistryMode,
    RegistryFingerprint,
)

from .errors import (
    RegistryError,
    DependencyCycleError,
    RouteConflictError,
    ConfigValidationError,
    CrossAppUsageError,
    ManifestValidationError,
    DuplicateAppError,
    FrozenManifestMismatchError,
    HotReloadError,
    ErrorSpan,
)

from .fingerprint import FingerprintGenerator


from .loader import (
    ManifestLoader,
    ManifestSource,
)

from .validator import (
    RegistryValidator,
    ValidationReport,
)

from .graph import (
    DependencyGraph,
    GraphNode,
)

__all__ = [
    # Core
    "Aquilary",
    "AquilaryRegistry",
    "RuntimeRegistry",
    "AppContext",
    "RegistryMode",
    
    # Errors
    "RegistryError",
    "DependencyCycleError",
    "RouteConflictError",
    "ConfigValidationError",
    "CrossAppUsageError",
    "ManifestValidationError",
    "DuplicateAppError",
    "FrozenManifestMismatchError",
    "HotReloadError",
    "ErrorSpan",
    
    # Fingerprint
    "FingerprintGenerator",
    "RegistryFingerprint",
    
    # Loader
    "ManifestLoader",
    "ManifestSource",
    
    # Validator
    "RegistryValidator",
    "ValidationReport",
    
    # Graph
    "DependencyGraph",
    "GraphNode",
]
