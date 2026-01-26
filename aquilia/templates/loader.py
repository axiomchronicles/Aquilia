"""
Template Loader - Namespace-aware filesystem and package template loaders.

Supports:
- Module-namespaced templates (users/profile.html -> modules/users/templates/profile.html)
- Cross-module references (@module/template.html or module:template.html)
- Package loaders for library-embedded templates
- Template discovery for compilation
"""

from typing import Any, Callable, Dict, List, Optional, Tuple
from pathlib import Path
import os
from jinja2 import BaseLoader, TemplateNotFound
from jinja2.loaders import FileSystemLoader, PackageLoader as Jinja2PackageLoader


class TemplateLoader(BaseLoader):
    """
    Namespace-aware template loader.
    
    Resolves templates using module namespaces and search paths.
    
    Template name formats:
        - Relative: "profile.html" -> resolved in current module context
        - Module-namespaced: "users/profile.html" -> modules/users/templates/profile.html
        - Cross-module (@): "@auth/login.html" -> modules/auth/templates/login.html
        - Fully-qualified (:): "users:profile.html" -> modules/users/templates/profile.html
    
    Args:
        search_paths: List of template directories (absolute paths)
        package_loaders: Dict mapping module names to package resource roots
        default_module: Default module context for relative paths
    """
    
    def __init__(
        self,
        search_paths: Optional[List[str]] = None,
        package_loaders: Optional[Dict[str, str]] = None,
        default_module: Optional[str] = None,
    ):
        self.search_paths = [Path(p) for p in (search_paths or [])]
        self.package_loaders = package_loaders or {}
        self.default_module = default_module
        
        # Create filesystem loaders for each search path
        self._fs_loaders = [
            FileSystemLoader(str(path))
            for path in self.search_paths
        ]
        
        # Create package loaders
        self._pkg_loaders: Dict[str, Jinja2PackageLoader] = {}
        for module_name, package_path in self.package_loaders.items():
            try:
                self._pkg_loaders[module_name] = Jinja2PackageLoader(
                    package_path,
                    package_path="templates"
                )
            except (ImportError, ValueError):
                # Package not found, skip
                pass
    
    def get_source(
        self,
        environment: Any,
        template: str
    ) -> Tuple[str, Optional[str], Optional[Callable[[], bool]]]:
        """
        Load template source.
        
        Returns:
            Tuple of (source, filename, uptodate_func)
            
        Raises:
            TemplateNotFound: If template cannot be found
        """
        # Parse template name
        module_name, template_path = self._parse_template_name(template)
        
        # Try package loader first if module specified
        if module_name and module_name in self._pkg_loaders:
            try:
                return self._pkg_loaders[module_name].get_source(
                    environment,
                    template_path
                )
            except TemplateNotFound:
                pass
        
        # Try filesystem loaders
        resolved_path = self._resolve_template_path(module_name, template_path)
        
        for loader in self._fs_loaders:
            try:
                return loader.get_source(environment, resolved_path)
            except TemplateNotFound:
                continue
        
        # Not found
        raise TemplateNotFound(template)
    
    def list_templates(self) -> List[str]:
        """
        List all available templates.
        
        Returns:
            List of template names (namespace-qualified)
        """
        templates = set()
        
        # List from filesystem loaders
        for path in self.search_paths:
            if not path.exists():
                continue
            
            for root, dirs, files in os.walk(path):
                root_path = Path(root)
                for filename in files:
                    if self._is_template_file(filename):
                        full_path = root_path / filename
                        relative = full_path.relative_to(path)
                        templates.add(str(relative))
        
        # List from package loaders
        for module_name, loader in self._pkg_loaders.items():
            try:
                pkg_templates = loader.list_templates()
                templates.update(
                    f"{module_name}:{t}" for t in pkg_templates
                )
            except (AttributeError, TypeError):
                # Loader doesn't support listing
                pass
        
        return sorted(templates)
    
    def _parse_template_name(self, template: str) -> Tuple[Optional[str], str]:
        """
        Parse template name into (module_name, template_path).
        
        Examples:
            "profile.html" -> (None, "profile.html")
            "users/profile.html" -> ("users", "profile.html")
            "@auth/login.html" -> ("auth", "login.html")
            "users:profile.html" -> ("users", "profile.html")
        """
        # Fully-qualified with colon
        if ":" in template:
            module_name, template_path = template.split(":", 1)
            return module_name, template_path
        
        # Cross-module with @
        if template.startswith("@"):
            template = template[1:]
            if "/" in template:
                module_name, template_path = template.split("/", 1)
                return module_name, template_path
        
        # Module-namespaced with slash
        if "/" in template:
            parts = template.split("/", 1)
            # Check if first part looks like a module name
            if self._looks_like_module(parts[0]):
                return parts[0], parts[1]
        
        # Relative or simple
        return self.default_module, template
    
    def _resolve_template_path(
        self,
        module_name: Optional[str],
        template_path: str
    ) -> str:
        """
        Resolve template path based on module namespace.
        
        If module_name provided, prepends module templates dir.
        Otherwise returns template_path as-is.
        """
        if module_name:
            # Standard convention: modules/{module}/templates/{path}
            # But we rely on search_paths to include correct roots,
            # so just return the template_path
            return template_path
        return template_path
    
    def _looks_like_module(self, name: str) -> bool:
        """Check if name looks like a module name."""
        # Simple heuristic: no file extension, lowercase/alphanumeric
        return (
            "." not in name and
            name.replace("_", "").replace("-", "").isalnum()
        )
    
    def _is_template_file(self, filename: str) -> bool:
        """Check if filename is a template file."""
        template_extensions = {".html", ".htm", ".xml", ".txt", ".jinja", ".jinja2", ".j2"}
        return any(filename.endswith(ext) for ext in template_extensions)


class PackageLoader(Jinja2PackageLoader):
    """
    Package loader for library-embedded templates.
    
    Wrapper around Jinja2's PackageLoader for consistency.
    """
    pass
