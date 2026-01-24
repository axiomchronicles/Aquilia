"""Add module to workspace command."""

from pathlib import Path
from typing import Optional, List

from ..utils.colors import info, dim
from ..generators import ModuleGenerator
from ..parsers import WorkspaceManifest


def add_module(
    name: str,
    depends_on: List[str],
    fault_domain: Optional[str] = None,
    route_prefix: Optional[str] = None,
    with_tests: bool = False,
    verbose: bool = False,
) -> Path:
    """
    Add a new module to the workspace.
    
    Args:
        name: Module name
        depends_on: List of module dependencies
        fault_domain: Custom fault domain
        route_prefix: Route prefix for the module
        with_tests: Generate test routes file
        verbose: Enable verbose output
    
    Returns:
        Path to created module
    """
    workspace_root = Path.cwd()
    manifest_path = workspace_root / 'aquilia.aq'
    
    if not manifest_path.exists():
        raise ValueError("Not in an Aquilia workspace (aquilia.aq not found)")
    
    if verbose:
        info(f"Adding module '{name}'...")
        if depends_on:
            info(f"  Dependencies: {', '.join(depends_on)}")
        if fault_domain:
            info(f"  Fault domain: {fault_domain}")
        if route_prefix:
            info(f"  Route prefix: {route_prefix}")
        if with_tests:
            info(f"  With test routes: Yes")
    
    # Load workspace manifest
    manifest = WorkspaceManifest.from_file(manifest_path)
    
    # Check if module already exists
    if name in manifest.modules:
        raise ValueError(f"Module '{name}' already exists")
    
    # Validate dependencies
    for dep in depends_on:
        if dep not in manifest.modules:
            raise ValueError(f"Dependency '{dep}' not found")
    
    # Generate module (always with controllers now)
    module_path = workspace_root / 'modules' / name
    
    generator = ModuleGenerator(
        name=name,
        path=module_path,
        depends_on=depends_on,
        fault_domain=fault_domain or name.upper(),
        route_prefix=route_prefix or f"/{name}",
        with_tests=with_tests,
    )
    
    generator.generate()
    
    # Update workspace manifest
    manifest.add_module(name, {
        'fault_domain': fault_domain or name.upper(),
        'route_prefix': route_prefix or f"/{name}",
        'depends_on': depends_on,
    })
    
    manifest.save(manifest_path)
    
    if verbose:
        dim("\nGenerated structure:")
        dim(f"  modules/{name}/")
        dim(f"    module.aq")
        dim(f"    controllers.py")
        dim(f"    services.py")
        dim(f"    faults.py")
        if with_tests:
            dim(f"    test_routes.py")
        dim(f"    __init__.py")
    
    return module_path
