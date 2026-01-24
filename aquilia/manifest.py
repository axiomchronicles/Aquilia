"""
AppManifest - Pure data-driven application manifest system.
No import-time side effects, fully serializable and inspectable.
"""

from typing import Any, Callable, Optional, Type, List, Tuple
from dataclasses import dataclass, field
import hashlib
import json


@dataclass
class AppManifest:
    """
    Base class for application manifests. All apps must declare a manifest
    that inherits from this class. Manifests are pure data - no side effects.
    """
    
    # Required fields
    name: str
    version: str
    
    # Optional configuration
    config: Optional[Type] = None
    
    # Import paths for components (lazy loaded)
    controllers: List[str] = field(default_factory=list)
    services: List[str] = field(default_factory=list)
    
    # Dependencies on other apps
    depends_on: List[str] = field(default_factory=list)
    
    # Middleware declarations: (import_path, kwargs)
    middlewares: List[Tuple[str, dict]] = field(default_factory=list)
    
    # Lifecycle hooks
    on_startup: Optional[Callable] = None
    on_shutdown: Optional[Callable] = None
    
    # Metadata
    description: str = ""
    author: str = ""
    
    def __post_init__(self):
        """Validate manifest structure."""
        if not self.name:
            raise ValueError("Manifest must have a name")
        if not self.version:
            raise ValueError("Manifest must have a version")
        
        # Validate name format (alphanumeric + underscore)
        if not self.name.replace("_", "").isalnum():
            raise ValueError(f"Invalid app name '{self.name}': must be alphanumeric with underscores")
    
    def to_dict(self) -> dict:
        """Serialize manifest to dictionary (for fingerprinting)."""
        return {
            "name": self.name,
            "version": self.version,
            "controllers": self.controllers,
            "services": self.services,
            "depends_on": self.depends_on,
            "middlewares": [
                {"path": path, "kwargs": kwargs}
                for path, kwargs in self.middlewares
            ],
            "description": self.description,
            "author": self.author,
        }
    
    def fingerprint(self) -> str:
        """Generate stable hash of manifest for reproducible deploys."""
        data = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()[:16]


class ManifestLoader:
    """Loads and validates application manifests."""
    
    @staticmethod
    def load_manifests(manifest_classes: List[Type[AppManifest]]) -> List[AppManifest]:
        """
        Instantiate manifest classes and validate them.
        
        Args:
            manifest_classes: List of AppManifest subclasses
            
        Returns:
            List of instantiated and validated manifests
        """
        manifests = []
        names_seen = set()
        
        for cls in manifest_classes:
            # Check if it's already an instance (AppManifest object)
            if isinstance(cls, AppManifest):
                manifest = cls
            # Check if it's a class that can be instantiated
            elif isinstance(cls, type):
                manifest = cls()
            else:
                raise TypeError(f"Expected AppManifest instance or class, got {type(cls)}")
            
            # Check for duplicate names
            if manifest.name in names_seen:
                raise ValueError(
                    f"Duplicate app name '{manifest.name}' found. "
                    f"Each app must have a unique name."
                )
            names_seen.add(manifest.name)
            
            manifests.append(manifest)
        
        return manifests
    
    @staticmethod
    def validate_manifest(manifest: AppManifest) -> List[str]:
        """
        Validate a single manifest and return list of warnings/errors.
        
        Returns:
            List of validation messages (empty if valid)
        """
        issues = []
        
        # Validate version format
        if not manifest.version or "." not in manifest.version:
            issues.append(f"App '{manifest.name}': version should follow semver (e.g., '1.0.0')")
        
        # Check for circular self-dependency
        if manifest.name in manifest.depends_on:
            issues.append(f"App '{manifest.name}': cannot depend on itself")
        
        # Validate middleware declarations
        for idx, (path, kwargs) in enumerate(manifest.middlewares):
            if not isinstance(path, str) or ":" not in path:
                issues.append(
                    f"App '{manifest.name}': middleware[{idx}] path must be "
                    f"'module:callable' format"
                )
            if not isinstance(kwargs, dict):
                issues.append(
                    f"App '{manifest.name}': middleware[{idx}] kwargs must be a dict"
                )
        
        return issues
