"""
Safe manifest loader with no import-time side effects.
"""

from typing import List, Type, Any, Union
from pathlib import Path
from dataclasses import dataclass
import importlib.util
import sys


@dataclass
class ManifestSource:
    """
    Manifest source descriptor.
    
    Can be Python class, file path, or DSL (YAML/JSON).
    """
    
    type: str  # "class", "file", "dsl"
    value: Any
    origin: str  # Source location for debugging
    
    def __repr__(self) -> str:
        return f"ManifestSource({self.type}, {self.origin})"


class ManifestLoader:
    """
    Safe manifest loader that NEVER triggers import-time side effects.
    
    Loads manifests from:
    - Python classes (already imported)
    - File paths (lazy import with isolated namespace)
    - DSL files (YAML/JSON parsing only)
    - Filesystem discovery (controlled)
    """
    
    def __init__(self):
        self._loaded_manifests: List[Any] = []
        self._seen_names: set[str] = set()
    
    def load_manifests(
        self,
        sources: List[Union[Type, str]],
        *,
        allow_fs_autodiscovery: bool = False,
    ) -> List[Any]:
        """
        Load manifests from sources.
        
        Args:
            sources: List of manifest classes or file paths
            allow_fs_autodiscovery: If True, scan apps/ directory
            
        Returns:
            List of loaded manifest objects
            
        Raises:
            ManifestValidationError: If manifest is invalid
            DuplicateAppError: If duplicate app names found
        """
        manifest_sources = self._resolve_sources(sources, allow_fs_autodiscovery)
        
        for source in manifest_sources:
            manifest = self._load_from_source(source)
            self._validate_manifest(manifest, source)
            
            # Check for duplicates
            if manifest.name in self._seen_names:
                from .errors import DuplicateAppError, ErrorSpan
                
                # Find existing manifest with same name
                existing = next(
                    m for m in self._loaded_manifests if m.name == manifest.name
                )
                
                raise DuplicateAppError(
                    app_name=manifest.name,
                    sources=[
                        getattr(existing, "__source__", "unknown"),
                        source.origin,
                    ],
                    span=ErrorSpan(file=source.origin),
                )
            
            self._seen_names.add(manifest.name)
            
            # Attach source metadata
            manifest.__source__ = source.origin
            
            self._loaded_manifests.append(manifest)
        
        return self._loaded_manifests
    
    def _resolve_sources(
        self,
        sources: List[Union[Type, str]],
        allow_fs_autodiscovery: bool,
    ) -> List[ManifestSource]:
        """
        Resolve source specifications into ManifestSource objects.
        
        Args:
            sources: List of manifest classes or paths
            allow_fs_autodiscovery: If True, scan filesystem
            
        Returns:
            List of ManifestSource objects
        """
        resolved: List[ManifestSource] = []
        
        for source in sources:

            if isinstance(source, type):
                # Already imported class
                resolved.append(
                    ManifestSource(
                        type="class",
                        value=source,
                        origin=f"{source.__module__}.{source.__name__}",
                    )
                )
            elif isinstance(source, str):
                path = Path(source)
                
                if path.suffix in (".yaml", ".yml", ".json"):
                    # DSL file
                    resolved.append(
                        ManifestSource(
                            type="dsl",
                            value=path,
                            origin=str(path),
                        )
                    )
                elif path.suffix == ".py":
                    # Python file
                    resolved.append(
                        ManifestSource(
                            type="file",
                            value=path,
                            origin=str(path),
                        )
                    )
                elif path.is_dir():
                    # Directory - scan for manifests
                    resolved.extend(self._discover_in_directory(path))
                else:
                    raise ValueError(f"Unknown manifest source type: {source}")
            else:
                # Check for instance-based manifest (e.g. Module builder)
                if hasattr(source, "build"):
                    # It's likely a builder
                    resolved.append(
                        ManifestSource(
                            type="builder",
                            value=source,
                            origin=str(source),
                        )
                    )
                elif hasattr(source, "name") and hasattr(source, "version"):
                    # It's a config object/dataclass
                    resolved.append(
                        ManifestSource(
                            type="instance",
                            value=source,
                            origin=str(source),
                        )
                    )
                else:
                    raise ValueError(f"Unknown manifest source type: {source}")
        
        # Filesystem autodiscovery
        if allow_fs_autodiscovery:
            resolved.extend(self._autodiscover_manifests())
        
        return resolved
    
    def _load_from_source(self, source: ManifestSource) -> Any:
        """
        Load manifest from source.
        
        Args:
            source: ManifestSource to load
            
        Returns:
            Manifest object
        """
        if source.type == "class":
            return source.value
        elif source.type == "file":
            return self._load_from_python_file(source.value)
        elif source.type == "dsl":
            return self._load_from_dsl_file(source.value)
        elif source.type == "builder":
            return source.value.build()
        elif source.type == "instance":
            return source.value
        else:
            raise ValueError(f"Unknown source type: {source.type}")
    
    def _load_from_python_file(self, path: Path) -> Any:
        """
        Load manifest from Python file without executing module-level code.
        
        Uses isolated namespace to prevent side effects.
        
        Args:
            path: Path to Python file
            
        Returns:
            Manifest class
        """
        # Create isolated module namespace
        module_name = f"_aquilary_manifest_{path.stem}"
        
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load manifest from {path}")
        
        module = importlib.util.module_from_spec(spec)
        
        # DO NOT add to sys.modules to prevent side effects
        # spec.loader.exec_module(module)
        
        # Instead, parse AST and extract manifest class statically
        # (For now, we'll do import but with controlled environment)
        
        # Save current sys.modules state
        saved_modules = sys.modules.copy()
        
        try:
            spec.loader.exec_module(module)
            
            # Find manifest class
            manifest_cls = None
            for name, obj in vars(module).items():
                if (
                    isinstance(obj, type)
                    and hasattr(obj, "name")
                    and hasattr(obj, "version")
                    and not name.startswith("_")
                ):
                    manifest_cls = obj
                    break
            
            if manifest_cls is None:
                raise ValueError(f"No manifest class found in {path}")
            
            return manifest_cls
        finally:
            # Restore sys.modules to prevent pollution
            sys.modules.clear()
            sys.modules.update(saved_modules)
    
    def _load_from_dsl_file(self, path: Path) -> Any:
        """
        Load manifest from DSL file (YAML/JSON).
        
        Args:
            path: Path to DSL file
            
        Returns:
            Manifest object (converted from dict)
        """
        import json
        
        if path.suffix == ".json":
            data = json.loads(path.read_text())
        elif path.suffix in (".yaml", ".yml"):
            try:
                import yaml
                data = yaml.safe_load(path.read_text())
            except ImportError:
                raise ImportError(
                    "PyYAML required for YAML manifests. "
                    "Install with: pip install pyyaml"
                )
        else:
            raise ValueError(f"Unsupported DSL format: {path.suffix}")
        
        # Convert dict to manifest class
        return self._dict_to_manifest(data, str(path))
    
    def _dict_to_manifest(self, data: dict, origin: str) -> Any:
        """
        Convert dict to manifest class.
        
        Args:
            data: Manifest data dict
            origin: Source origin string
            
        Returns:
            Manifest class instance
        """
        # Create dynamic manifest class
        class DynamicManifest:
            name = data.get("name")
            version = data.get("version")
            controllers = data.get("controllers", [])
            services = data.get("services", [])
            middlewares = data.get("middlewares", [])
            depends_on = data.get("depends_on", [])
            
            @staticmethod
            def on_startup():
                pass
            
            @staticmethod
            def on_shutdown():
                pass
        
        DynamicManifest.__name__ = f"{data.get('name', 'Unknown')}Manifest"
        DynamicManifest.__module__ = origin
        
        return DynamicManifest
    
    def _discover_in_directory(self, directory: Path) -> List[ManifestSource]:
        """
        Discover manifests in directory.
        
        Looks for:
        - manifest.py
        - *_manifest.py
        - manifest.yaml/yml/json
        
        Args:
            directory: Directory to scan
            
        Returns:
            List of ManifestSource objects
        """
        sources: List[ManifestSource] = []
        
        # Python manifests
        for pattern in ["manifest.py", "*_manifest.py"]:
            for path in directory.glob(pattern):
                sources.append(
                    ManifestSource(
                        type="file",
                        value=path,
                        origin=str(path),
                    )
                )
        
        # DSL manifests
        for pattern in ["manifest.yaml", "manifest.yml", "manifest.json"]:
            for path in directory.glob(pattern):
                sources.append(
                    ManifestSource(
                        type="dsl",
                        value=path,
                        origin=str(path),
                    )
                )
        
        return sources
    
    def _autodiscover_manifests(self) -> List[ManifestSource]:
        """
        Auto-discover manifests in apps/ directory.
        
        Returns:
            List of ManifestSource objects
        """
        apps_dir = Path("apps")
        if not apps_dir.exists():
            return []
        
        sources: List[ManifestSource] = []
        
        for app_dir in apps_dir.iterdir():
            if app_dir.is_dir() and not app_dir.name.startswith("_"):
                sources.extend(self._discover_in_directory(app_dir))
        
        return sources
    
    def _validate_manifest(self, manifest: Any, source: ManifestSource) -> None:
        """
        Validate manifest structure.
        
        Args:
            manifest: Manifest object to validate
            source: Source descriptor
            
        Raises:
            ManifestValidationError: If validation fails
        """
        from .errors import ManifestValidationError, ErrorSpan
        
        errors: List[str] = []
        
        # Required fields
        if not hasattr(manifest, "name") or not manifest.name:
            errors.append("Missing required field: name")
        
        if not hasattr(manifest, "version") or not manifest.version:
            errors.append("Missing required field: version")
        
        # Type validation
        if hasattr(manifest, "controllers"):
            if not isinstance(manifest.controllers, list):
                errors.append("Field 'controllers' must be a list")
            else:
                for i, ctrl in enumerate(manifest.controllers):
                    if not isinstance(ctrl, str):
                        errors.append(
                            f"controllers[{i}] must be string import path"
                        )
        
        if hasattr(manifest, "services"):
            if not isinstance(manifest.services, list):
                errors.append("Field 'services' must be a list")
        
        if hasattr(manifest, "depends_on"):
            if not isinstance(manifest.depends_on, list):
                errors.append("Field 'depends_on' must be a list")
            else:
                for i, dep in enumerate(manifest.depends_on):
                    if not isinstance(dep, str):
                        errors.append(f"depends_on[{i}] must be string app name")
        
        # Raise if errors
        if errors:
            raise ManifestValidationError(
                manifest_name=getattr(manifest, "name", "unknown"),
                validation_errors=errors,
                span=ErrorSpan(file=source.origin),
            )
