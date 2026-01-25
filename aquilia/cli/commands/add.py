"""Add module to workspace command."""

from pathlib import Path
from typing import Optional, List

from ..utils.colors import info, dim
from ..generators import ModuleGenerator


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
    workspace_file = workspace_root / 'workspace.py'
    
    if not workspace_file.exists():
        raise ValueError("Not in an Aquilia workspace (workspace.py not found)")
    
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
    
    # Check if modules directory exists
    modules_dir = workspace_root / 'modules'
    if not modules_dir.exists():
        modules_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if module already exists
    module_path = modules_dir / name
    if module_path.exists():
        raise ValueError(f"Module '{name}' already exists")
    
    # Parse existing workspace.py to find existing modules
    workspace_content = workspace_file.read_text()
    existing_modules = []
    
    # Simple regex to find .module() calls
    import re
    # (?m) enables multiline mode, ^ matches start of line, \s* matches indentation
    module_pattern = r'(?m)^\s*\.module\(Module\("([^"]+)"\)'
    existing_modules = re.findall(module_pattern, workspace_content)
    
    # Validate dependencies
    for dep in depends_on:
        if dep not in existing_modules:
            raise ValueError(f"Dependency '{dep}' not found in workspace")
    
    # Generate module structure
    generator = ModuleGenerator(
        name=name,
        path=module_path,
        depends_on=depends_on,
        fault_domain=fault_domain or name.upper(),
        route_prefix=route_prefix or f"/{name}",
        with_tests=with_tests,
    )
    
    generator.generate()
    
    # Update workspace.py to include the new module
    # Find the line with "# Add modules here:" and add the module after it
    lines = workspace_content.split('\n')
    insert_index = None
    
    for i, line in enumerate(lines):
        if '# Add modules here:' in line:
            insert_index = i + 1
            break
    
    if insert_index is not None:
        # Build the module line
        module_line = f'    .module(Module("{name}").route_prefix("{route_prefix or "/" + name}"))'
        
        # Check if there are already modules (look for existing .module() calls after the comment)
        # Insert after the comment line
        lines.insert(insert_index, module_line)
        
        # Write back to file
        workspace_file.write_text('\n'.join(lines))
        
        if verbose:
            info(f"\n✓ Updated workspace.py with module '{name}'")
    else:
        if verbose:
            warning = __import__('aquilia.cli.utils.colors', fromlist=['warning']).warning
            warning("\n⚠ Could not auto-update workspace.py")
            info(f"  Please manually add to workspace.py:")
            info(f'    .module(Module("{name}").route_prefix("{route_prefix or "/" + name}"))')
    
    if verbose:
        dim("\nGenerated structure:")
        dim(f"  modules/{name}/")
        dim(f"    manifest.py")
        dim(f"    controllers.py")
        dim(f"    services.py")
        dim(f"    faults.py")
        if with_tests:
            dim(f"    test_routes.py")
        dim(f"    __init__.py")
    
    return module_path

