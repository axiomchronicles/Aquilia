"""
AquilaTemplates - Manifest Integration

Integration between template system and Aquilia manifest system.
Enables auto-discovery of template directories from module.aq files.

Features:
- Auto-discover templates/ directories in modules
- Read templates: section from manifest files
- Configure loader search paths from manifest
- Compile templates as part of crous artifact generation
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
import json

logger = logging.getLogger(__name__)


# ============================================================================
# Manifest Discovery
# ============================================================================


class TemplateManifestConfig:
    """
    Configuration for templates from manifest file.
    
    Example module.aq:
        templates:
          enabled: true
          search_paths:
            - ./templates
            - ./themes/default
          precompile: true
          cache: crous
    """
    
    def __init__(self, manifest_data: Dict[str, Any]):
        self.raw = manifest_data.get("templates", {})
        self.enabled = self.raw.get("enabled", True)
        self.search_paths = self.raw.get("search_paths", [])
        self.precompile = self.raw.get("precompile", False)
        self.cache_type = self.raw.get("cache", "memory")
    
    @classmethod
    def from_file(cls, manifest_path: Path) -> "TemplateManifestConfig":
        """Load from module.aq file."""
        try:
            with open(manifest_path, 'r') as f:
                data = json.load(f)
            return cls(data)
        except Exception as e:
            logger.warning(f"Failed to load manifest {manifest_path}: {e}")
            return cls({})


def discover_template_directories(
    root_path: Optional[Path] = None,
    scan_manifests: bool = True
) -> List[Path]:
    """
    Discover template directories in project.
    
    Discovery strategy:
    1. Convention: Look for {module}/templates/ directories
    2. Manifest: Read templates.search_paths from module.aq files
    3. Default: ./templates/
    
    Args:
        root_path: Project root (defaults to cwd)
        scan_manifests: Whether to scan module.aq files
    
    Returns:
        List of discovered template directories
    """
    if not root_path:
        root_path = Path.cwd()
    
    discovered = []
    
    # Strategy 1: Convention-based discovery
    # Look for any directory named "templates"
    for templates_dir in root_path.rglob("templates"):
        if templates_dir.is_dir():
            # Skip hidden directories and venv
            if any(part.startswith('.') or part == 'env' for part in templates_dir.parts):
                continue
            
            discovered.append(templates_dir)
            logger.debug(f"Discovered template directory: {templates_dir}")
    
    # Strategy 2: Manifest-based discovery
    if scan_manifests:
        manifest_dirs = discover_from_manifests(root_path)
        discovered.extend(manifest_dirs)
    
    # Strategy 3: Default fallback
    default_templates = root_path / "templates"
    if default_templates not in discovered and default_templates.exists():
        discovered.append(default_templates)
    
    # Deduplicate and sort
    unique_dirs = list(set(discovered))
    unique_dirs.sort()
    
    logger.info(f"Discovered {len(unique_dirs)} template directories")
    return unique_dirs


def discover_from_manifests(root_path: Path) -> List[Path]:
    """
    Discover template directories from module.aq manifest files.
    
    Reads templates.search_paths from all module.aq files in project.
    
    Args:
        root_path: Project root
    
    Returns:
        List of template directories from manifests
    """
    manifest_dirs = []
    
    # Find all module.aq files
    for manifest_file in root_path.rglob("module.aq"):
        # Skip hidden directories and venv
        if any(part.startswith('.') or part == 'env' for part in manifest_file.parts):
            continue
        
        try:
            config = TemplateManifestConfig.from_file(manifest_file)
            
            if not config.enabled:
                continue
            
            # Resolve search paths relative to manifest directory
            manifest_dir = manifest_file.parent
            
            for search_path in config.search_paths:
                path = manifest_dir / search_path
                if path.exists():
                    manifest_dirs.append(path.resolve())
                    logger.debug(
                        f"Discovered from manifest {manifest_file}: {path}"
                    )
        
        except Exception as e:
            logger.warning(f"Error processing manifest {manifest_file}: {e}")
    
    return manifest_dirs


# ============================================================================
# Module Template Namespaces
# ============================================================================


class ModuleTemplateRegistry:
    """
    Registry mapping module names to template directories.
    
    Enables namespace resolution: @auth/login.html -> auth_module/templates/login.html
    """
    
    def __init__(self):
        self.registry: Dict[str, Path] = {}
    
    def register(self, module_name: str, templates_dir: Path) -> None:
        """
        Register module's template directory.
        
        Args:
            module_name: Module name (e.g., "auth", "blog")
            templates_dir: Path to module's templates directory
        """
        self.registry[module_name] = templates_dir
        logger.debug(f"Registered template namespace: {module_name} -> {templates_dir}")
    
    def resolve(self, module_name: str) -> Optional[Path]:
        """
        Resolve module name to templates directory.
        
        Args:
            module_name: Module name to resolve
        
        Returns:
            Templates directory path or None
        """
        return self.registry.get(module_name)
    
    def discover_and_register(self, root_path: Optional[Path] = None) -> None:
        """
        Auto-discover and register all module templates.
        
        Scans for patterns:
        - myapp/auth/templates/ -> register as "auth"
        - myapp/blog/templates/ -> register as "blog"
        """
        if not root_path:
            root_path = Path.cwd()
        
        # Look for module structures with templates/
        for templates_dir in root_path.rglob("templates"):
            if not templates_dir.is_dir():
                continue
            
            # Skip hidden and env
            if any(part.startswith('.') or part == 'env' for part in templates_dir.parts):
                continue
            
            # Extract module name (parent directory)
            module_name = templates_dir.parent.name
            
            # Don't register root-level "templates"
            if templates_dir.parent == root_path:
                continue
            
            self.register(module_name, templates_dir)
    
    def to_dict(self) -> Dict[str, str]:
        """Serialize registry to dictionary."""
        return {
            name: str(path) for name, path in self.registry.items()
        }


# ============================================================================
# Manifest-driven Precompilation
# ============================================================================


def should_precompile_module(manifest_path: Path) -> bool:
    """
    Check if module templates should be precompiled.
    
    Reads templates.precompile from manifest.
    
    Args:
        manifest_path: Path to module.aq
    
    Returns:
        True if templates should be precompiled
    """
    config = TemplateManifestConfig.from_file(manifest_path)
    return config.precompile


def get_cache_strategy(manifest_path: Path) -> str:
    """
    Get cache strategy from manifest.
    
    Reads templates.cache from manifest.
    
    Args:
        manifest_path: Path to module.aq
    
    Returns:
        Cache strategy: "memory", "crous", "redis", "none"
    """
    config = TemplateManifestConfig.from_file(manifest_path)
    return config.cache_type


# ============================================================================
# Integration with Crous Artifacts
# ============================================================================


def generate_template_manifest(
    template_dirs: List[Path],
    output_path: Path
) -> None:
    """
    Generate template manifest for crous artifacts.
    
    Creates templates.json with metadata about all templates
    for inclusion in crous artifact.
    
    Args:
        template_dirs: List of template directories
        output_path: Path to write templates.json
    """
    manifest = {
        "version": "1.0",
        "generated_at": None,  # Will be filled by caller
        "search_paths": [str(p) for p in template_dirs],
        "templates": {},
    }
    
    # Scan all templates
    for template_dir in template_dirs:
        for template_file in template_dir.rglob("*.html"):
            rel_path = template_file.relative_to(template_dir)
            template_name = str(rel_path)
            
            manifest["templates"][template_name] = {
                "path": str(template_file),
                "size": template_file.stat().st_size,
                "mtime": template_file.stat().st_mtime,
            }
    
    # Write manifest
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    logger.info(f"Generated template manifest: {output_path}")


# ============================================================================
# Enhanced Loader Factory
# ============================================================================


def create_manifest_aware_loader(
    root_path: Optional[Path] = None,
    scan_manifests: bool = True
):
    """
    Create TemplateLoader with manifest-based auto-discovery.
    
    Factory function that discovers template directories from
    manifests and conventions.
    
    Args:
        root_path: Project root (defaults to cwd)
        scan_manifests: Whether to scan module.aq files
    
    Returns:
        Configured TemplateLoader instance
    """
    from .loader import TemplateLoader
    
    # Discover template directories
    search_paths = discover_template_directories(root_path, scan_manifests)
    
    if not search_paths:
        logger.warning("No template directories discovered, using default")
        search_paths = [Path.cwd() / "templates"]
    
    # Create loader
    loader = TemplateLoader(search_paths=search_paths)
    
    logger.info(
        f"Created manifest-aware loader with {len(search_paths)} paths"
    )
    
    return loader


def create_module_registry(root_path: Optional[Path] = None) -> ModuleTemplateRegistry:
    """
    Create and populate module template registry.
    
    Factory function for module namespace resolution.
    
    Args:
        root_path: Project root (defaults to cwd)
    
    Returns:
        Populated ModuleTemplateRegistry
    """
    registry = ModuleTemplateRegistry()
    registry.discover_and_register(root_path)
    return registry
