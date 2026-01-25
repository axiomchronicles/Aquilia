"""Development server command."""

import sys
import os
import re
import importlib
from pathlib import Path
from typing import Optional, Dict, List, Set


def _discover_and_update_manifests(workspace_root: Path, verbose: bool = False) -> None:
    """
    Discover controllers and services in all modules and auto-update manifest.py files.
    
    This function:
    1. Scans all modules for controllers and services
    2. Compares with manifest.py declarations
    3. Automatically updates manifest.py with any missing declarations
    4. Provides visibility into what was discovered vs declared
    
    Args:
        workspace_root: Path to workspace root
        verbose: Enable verbose output
    """
    from aquilia.utils.scanner import PackageScanner
    
    modules_dir = workspace_root / "modules"
    if not modules_dir.exists():
        return
    
    scanner = PackageScanner()
    
    # Discover all modules with manifest.py
    for module_dir in modules_dir.iterdir():
        if not module_dir.is_dir() or module_dir.name.startswith('_'):
            continue
        
        manifest_path = module_dir / "manifest.py"
        if not manifest_path.exists():
            continue
        
        module_name = module_dir.name
        base_package = f"modules.{module_name}"
        
        try:
            # Discover Controllers
            discovered_controllers = []
            try:
                controllers = scanner.scan_package(
                    f"{base_package}.controllers",
                    predicate=lambda cls: cls.__name__.endswith("Controller"),
                )
                test_routes = scanner.scan_package(
                    f"{base_package}.test_routes",
                    predicate=lambda cls: cls.__name__.endswith("Controller"),
                )
                discovered_controllers = sorted(list(set(
                    f"{c.__module__}:{c.__name__}" for c in controllers + test_routes
                )))
            except Exception as e:
                if verbose:
                    print(f"  ⚠️  Could not scan controllers for {module_name}: {e}")
            
            # Discover Services
            discovered_services = []
            try:
                services = scanner.scan_package(
                    f"{base_package}.services",
                    predicate=lambda cls: cls.__name__.endswith("Service") or hasattr(cls, "__di_scope__"),
                )
                discovered_services = sorted(list(set(
                    f"{s.__module__}:{s.__name__}" for s in services
                )))
            except Exception as e:
                if verbose:
                    print(f"  ⚠️  Could not scan services for {module_name}: {e}")
            
            # Parse existing manifest content
            manifest_content = manifest_path.read_text()
            
            # Extract existing services and controllers from manifest
            existing_services = _extract_list_from_manifest(manifest_content, "services=")
            existing_controllers = _extract_list_from_manifest(manifest_content, "controllers=")
            
            # Find what's missing
            new_services = [s for s in discovered_services if s not in existing_services]
            new_controllers = [c for c in discovered_controllers if c not in existing_controllers]
            
            # If there are new items, update the manifest
            if new_services or new_controllers:
                updated_content = manifest_content
                
                # Update services
                if new_services:
                    all_services = existing_services + new_services
                    old_services_str = _extract_services_block(manifest_content)
                    new_services_str = _generate_services_block(all_services)
                    updated_content = updated_content.replace(old_services_str, new_services_str)
                
                # Update controllers
                if new_controllers:
                    all_controllers = existing_controllers + new_controllers
                    old_controllers_str = _extract_controllers_block(manifest_content)
                    new_controllers_str = _generate_controllers_block(all_controllers)
                    updated_content = updated_content.replace(old_controllers_str, new_controllers_str)
                
                # Write updated manifest
                manifest_path.write_text(updated_content)
                
                if verbose:
                    print(f"\n  ✅ Updated manifest for '{module_name}':")
                    if new_services:
                        print(f"     Added {len(new_services)} service(s)")
                        for s in new_services:
                            print(f"       - {s}")
                    if new_controllers:
                        print(f"     Added {len(new_controllers)} controller(s)")
                        for c in new_controllers:
                            print(f"       - {c}")
            
        except Exception as e:
            if verbose:
                print(f"  ⚠️  Error updating manifest for {module_name}: {e}")


def _extract_list_from_manifest(content: str, key: str) -> List[str]:
    """
    Extract list items from manifest.py.
    
    Args:
        content: Manifest file content
        key: The field to extract (e.g., "services=" or "controllers=")
    
    Returns:
        List of extracted items
    """
    try:
        # Find the pattern: key followed by [ ... ]
        pattern = rf'{re.escape(key)}\s*\[(.*?)\]'
        match = re.search(pattern, content, re.DOTALL)
        if not match:
            return []
        
        list_content = match.group(1)
        # Extract quoted strings
        items = re.findall(r'"([^"]*)"', list_content)
        return items
    except Exception:
        return []


def _extract_services_block(content: str) -> str:
    """Extract the services=[ ... ] block from manifest."""
    pattern = r'#\s*Services with detailed DI configuration\s*\n\s*services=\s*\[(.*?)\],\s*\n'
    match = re.search(pattern, content, re.DOTALL)
    if match:
        return match.group(0)
    return ""


def _extract_controllers_block(content: str) -> str:
    """Extract the controllers=[ ... ] block from manifest."""
    pattern = r'#\s*Controllers with routing\s*\n\s*controllers=\s*\[(.*?)\],\s*\n'
    match = re.search(pattern, content, re.DOTALL)
    if match:
        return match.group(0)
    return ""


def _generate_services_block(services: List[str]) -> str:
    """Generate the services=[ ... ] block for manifest."""
    if not services:
        return '    # Services with detailed DI configuration\n    services=[],\n'
    
    items = ",\n        ".join(f'"{s}"' for s in services)
    return f'''    # Services with detailed DI configuration
    services=[
        {items},
    ],
'''


def _generate_controllers_block(controllers: List[str]) -> str:
    """Generate the controllers=[ ... ] block for manifest."""
    if not controllers:
        return '    # Controllers with routing\n    controllers=[],\n'
    
    items = ",\n        ".join(f'"{c}"' for c in controllers)
    return f'''    # Controllers with routing
    controllers=[
        {items},
    ],
'''


def _discover_and_display_routes(workspace_root: Path, verbose: bool = False) -> None:
    """
    Discover all modules and their routes before starting server.
    
    Args:
        workspace_root: Path to workspace root
        verbose: Enable verbose output
    """
    try:
        from ..generators.workspace import WorkspaceGenerator
        
        # Initialize generator
        generator = WorkspaceGenerator(
            name=workspace_root.name,
            path=workspace_root
        )
        
        # Discover modules
        discovered = generator._discover_modules()
        
        if not discovered:
            return
        
        # Sort by dependencies
        sorted_names = generator._resolve_dependencies(discovered)
        
        print("\n📍 Discovered Routes & Modules")
        print("=" * 70)
        
        # Display module table
        print(f"\n{'Module':<20} {'Route Prefix':<25} {'Version':<12} {'Tags':<15}")
        print(f"{'-'*20} {'-'*25} {'-'*12} {'-'*15}")
        
        for mod_name in sorted_names:
            mod = discovered[mod_name]
            tags = ", ".join(mod.get('tags', [])[:2]) if mod.get('tags') else ""
            route = mod['route_prefix']
            version = mod['version']
            print(f"{mod_name:<20} {route:<25} {version:<12} {tags:<15}")
        
        # Display dependency graph if any module has dependencies
        has_deps = any(mod.get('depends_on') for mod in discovered.values())
        if has_deps:
            print(f"\n🔗 Dependency Graph:")
            for mod_name in sorted_names:
                mod = discovered[mod_name]
                deps = mod.get('depends_on', [])
                if deps:
                    deps_str = " → ".join(deps)
                    print(f"  {mod_name}: {deps_str}")
                else:
                    print(f"  {mod_name}: (no dependencies)")
        
        # Summary
        print(f"\n📊 Summary:")
        with_services = sum(1 for m in discovered.values() if m['has_services'])
        with_controllers = sum(1 for m in discovered.values() if m['has_controllers'])
        with_middleware = sum(1 for m in discovered.values() if m['has_middleware'])
        
        print(f"  Total Modules: {len(discovered)}")
        print(f"  With Services: {with_services}")
        print(f"  With Controllers: {with_controllers}")
        print(f"  With Middleware: {with_middleware}")
        
        # Validation status
        validation = generator._validate_modules(discovered)
        if validation['errors']:
            print(f"\n⚠️  Validation Errors: {len(validation['errors'])}")
            for error in validation['errors']:
                print(f"    - {error}")
        elif validation['warnings']:
            print(f"\n⚠️  Validation Warnings: {len(validation['warnings'])}")
            for warning in validation['warnings'][:3]:
                print(f"    - {warning}")
        else:
            print(f"\n✅ All modules validated!")
        
        print(f"{'='*70}\n")
        
        # Write discovery report to file
        _write_discovery_report(workspace_root, discovered, sorted_names, validation)
    
    except Exception as e:
        if verbose:
            print(f"⚠️  Could not discover routes: {e}\n")
        # Continue even if discovery fails


def _write_discovery_report(workspace_root: Path, discovered: Dict, sorted_names: List[str], validation: Dict) -> None:
    """
    Write discovery report to routes.md file.
    
    Args:
        workspace_root: Path to workspace root
        discovered: Dictionary of discovered modules
        sorted_names: Module names in load order
        validation: Validation results
    """
    try:
        report_lines = [
            "# 📍 Auto-Discovered Routes & Modules\n",
            f"*Generated: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n",
            "\n## Module Routes\n",
        ]
        
        # Module table
        report_lines.append("| Module | Route Prefix | Version | Tags | Components |\n")
        report_lines.append("|--------|--------------|---------|------|------------|\n")
        
        for mod_name in sorted_names:
            mod = discovered[mod_name]
            tags = ", ".join(mod.get('tags', [])[:3]) if mod.get('tags') else "-"
            components = []
            if mod['has_services']:
                components.append("Services")
            if mod['has_controllers']:
                components.append("Controllers")
            if mod['has_middleware']:
                components.append("Middleware")
            comp_str = ", ".join(components) if components else "-"
            
            report_lines.append(
                f"| {mod_name} | `{mod['route_prefix']}` | {mod['version']} | {tags} | {comp_str} |\n"
            )
        
        # Dependencies section
        has_deps = any(mod.get('depends_on') for mod in discovered.values())
        if has_deps:
            report_lines.append("\n## Dependencies\n\n")
            for mod_name in sorted_names:
                mod = discovered[mod_name]
                deps = mod.get('depends_on', [])
                if deps:
                    deps_str = " → ".join(deps)
                    report_lines.append(f"- **{mod_name}** depends on: {deps_str}\n")
                else:
                    report_lines.append(f"- **{mod_name}** (no dependencies)\n")
        
        # Statistics
        with_services = sum(1 for m in discovered.values() if m['has_services'])
        with_controllers = sum(1 for m in discovered.values() if m['has_controllers'])
        with_middleware = sum(1 for m in discovered.values() if m['has_middleware'])
        
        report_lines.append("\n## Statistics\n\n")
        report_lines.append(f"- **Total Modules**: {len(discovered)}\n")
        report_lines.append(f"- **With Services**: {with_services}\n")
        report_lines.append(f"- **With Controllers**: {with_controllers}\n")
        report_lines.append(f"- **With Middleware**: {with_middleware}\n")
        report_lines.append(f"- **Load Order**: {' → '.join(sorted_names)}\n")
        
        # Validation section
        report_lines.append("\n## Validation\n\n")
        if validation['errors']:
            report_lines.append(f"❌ **Errors**: {len(validation['errors'])}\n\n")
            for error in validation['errors']:
                report_lines.append(f"- {error}\n")
        elif validation['warnings']:
            report_lines.append(f"⚠️ **Warnings**: {len(validation['warnings'])}\n\n")
            for warning in validation['warnings']:
                report_lines.append(f"- {warning}\n")
        else:
            report_lines.append("✅ **Status**: All modules validated!\n")
        
        # Write report
        report_file = workspace_root / "ROUTES.md"
        report_file.write_text("".join(report_lines))
    
    except Exception:
        # Silently fail - don't interrupt server startup
        pass



def run_dev_server(
    mode: str = 'dev',
    host: str = '127.0.0.1',
    port: int = 8000,
    reload: bool = True,
    verbose: bool = False,
) -> None:
    """
    Start development server using uvicorn.
    
    Args:
        mode: Runtime mode (dev, test)
        host: Server host
        port: Server port
        reload: Enable hot-reload
        verbose: Enable verbose output
    """
    try:
        import uvicorn
    except ImportError:
        raise ImportError(
            "uvicorn is required to run the development server.\n"
            "Install it with: pip install uvicorn\n"
            "Or with extras: pip install 'aquilia[server]'"
        )
    
    workspace_root = Path.cwd()
    
    # Add workspace root to Python path for imports
    if str(workspace_root) not in sys.path:
        sys.path.insert(0, str(workspace_root))
    
    # Set environment variables
    os.environ['AQUILIA_ENV'] = mode
    os.environ['AQUILIA_WORKSPACE'] = str(workspace_root)
    
    # Strategy 1: Check for workspace configuration (workspace.py) and auto-create app
    workspace_config = workspace_root / "workspace.py"
    if workspace_config.exists():
        if verbose:
            print("✓ Found workspace configuration: workspace.py")
        
        # Create a runtime app loader
        app_module = _create_workspace_app(workspace_root, mode, verbose)
        
        if verbose:
            print(f"  Using workspace-generated app")
    else:
        # Strategy 2: Look for existing app module
        app_module = _find_app_module(workspace_root, verbose)
        
        if not app_module:
            raise ValueError(
                "Could not find ASGI application.\n\n"
                "Expected one of:\n"
                "  1. Workspace configuration: workspace.py (recommended)\n"
                "  2. main.py with 'app' variable\n"
                "  3. app.py with 'app' variable\n"
                "  4. server.py with 'app' or 'server' variable\n\n"
                "For workspace-based projects:\n"
                "  Run: aq init workspace <name>\n"
                "  Then: aq add module <module_name>\n\n"
                "For standalone apps, create main.py:\n"
                "  from aquilia import AquiliaServer\n"
                "  from aquilia.manifest import AppManifest\n\n"
                "  class MyAppManifest(AppManifest):\n"
                "      name = 'myapp'\n"
                "      version = '1.0.0'\n"
                "      controllers = []\n\n"
                "  server = AquiliaServer(manifests=[MyAppManifest])\n"
                "  app = server.app\n"
            )
    
    if verbose:
        print(f"\n🚀 Starting Aquilia development server...")
        print(f"  Mode: {mode}")
        print(f"  Host: {host}:{port}")
        print(f"  Reload: {reload}")
        print(f"  App: {app_module}")
        print()
    
    # AUTO-DISCOVER & UPDATE MANIFESTS BEFORE SERVER START
    print("🔍 Auto-discovering controllers and services...")
    _discover_and_update_manifests(workspace_root, verbose)
    
    # Discover and display all routes before starting server
    _discover_and_display_routes(workspace_root, verbose)
    
    # Configure uvicorn
    config = uvicorn.Config(
        app=app_module,
        host=host,
        port=port,
        reload=reload,
        reload_dirs=[str(workspace_root)] if reload else None,
        log_level="debug" if verbose else "info",
        access_log=True,
        use_colors=True,
    )
    
    server = uvicorn.Server(config)
    server.run()


def _create_workspace_app(workspace_root: Path, mode: str, verbose: bool = False) -> str:
    """
    Create an ASGI app from workspace configuration.
    
    This generates a runtime app loader module that:
    1. Loads the workspace configuration (workspace.py)
    2. Discovers and loads module manifests (manifest.py)
    3. Creates AquiliaServer with all manifests
    4. Returns the ASGI app
    
    Args:
        workspace_root: Path to workspace root
        mode: Runtime mode (dev, test, prod)
        verbose: Enable verbose output
        
    Returns:
        Module path (e.g., "runtime.app:app")
    """
    runtime_dir = workspace_root / "runtime"
    runtime_dir.mkdir(exist_ok=True)
    
    # Create runtime app loader
    app_file = runtime_dir / "app.py"
    
    # Generate the app loader code
    app_code = _generate_workspace_app_code(workspace_root, mode, verbose)
    
    # Write the app file
    app_file.write_text(app_code)
    
    if verbose:
        print(f"  Generated runtime app: {app_file}")
    
    # Return the module path
    return "runtime.app:app"


def _generate_workspace_app_code(workspace_root: Path, mode: str, verbose: bool = False) -> str:
    """
    Generate Python code for workspace app loader.
    
    Returns:
        Python code as string
    """
    from datetime import datetime
    import re
    
    # Load workspace modules from workspace.py
    workspace_file = workspace_root / "workspace.py"
    workspace_content = workspace_file.read_text()
    
    # Extract workspace info
    name_match = re.search(r'Workspace\("([^"]+)"', workspace_content)
    workspace_name = name_match.group(1) if name_match else "aquilia-workspace"
    
    # Extract modules
    # (?m) enables multiline mode, ^ matches start of line, \s* matches indentation
    # Updated regex to handle Module with parameters: Module("name", version=..., ...)
    modules = re.findall(r'(?m)^\s*\.module\(Module\("([^"]+)"[^)]*\)', workspace_content)
    
    if verbose:
        print(f"  Found modules: {', '.join(modules)}")
    
    # Generate timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Generate the code
    code = f'''"""
Auto-generated Aquilia ASGI Application
========================================

This file is automatically generated by the Aquilia CLI from your workspace configuration.
It creates an ASGI-compliant application that can be run with any ASGI server.

Generated by: aq run
Workspace: {workspace_name}
Timestamp: {timestamp}

DO NOT EDIT - This file is regenerated on each run.

Usage:
  Development: aq run
  Production:  uvicorn runtime.app:app --workers 4
  With gunicorn: gunicorn runtime.app:app -k uvicorn.workers.UvicornWorker

Learn more: https://docs.aquilia.dev/
"""

import sys
from pathlib import Path

# Add workspace root to path
workspace_root = Path(__file__).parent.parent
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

from aquilia import AquiliaServer
from aquilia.config import ConfigLoader

'''
    
    # Import module manifests
    manifest_vars = []
    
    for module_name in modules:
        code += f"from modules.{module_name}.manifest import manifest as {module_name}_manifest\n"
        manifest_vars.append(f"{module_name}_manifest")
        
        if verbose:
            print(f"  Loaded module: {module_name}")
            
    manifests_str = ", ".join(manifest_vars)
    
    # Build apps config
    apps_config = "\n".join([
        f'config.config_data["apps"]["{m}"] = {{}}'
        for m in modules
    ])
    
    code += f'''
# Create configuration
config = ConfigLoader.load(paths=["workspace.py"])

# Merge config data directly
config.config_data["debug"] = True
config.config_data["mode"] = "{mode}"

# Initialize apps config for each module
config.config_data["apps"] = {{}}
{apps_config}

# Build the apps namespace (required by Aquilary)
config._build_apps_namespace()

# Create server with all module manifests
server = AquiliaServer(
    manifests=[{manifests_str}],
    config=config,
)

# ASGI application
app = server.app

print("✓ Aquilia workspace app loaded")
print(f"  Workspace: {workspace_name}")
print(f"  Modules: {len(modules)}")
'''
    
    return code


def _find_app_module(workspace_root: Path, verbose: bool = False) -> Optional[str]:
    """
    Find the ASGI app module.
    
    Looks for:
    1. main.py with 'app' or 'application'
    2. app.py with 'app' or 'application'  
    3. server.py with 'app' or 'server'
    
    Returns:
        Module path (e.g., "main:app") or None if not found
    """
    candidates = [
        ("main.py", ["app", "application", "server"]),
        ("app.py", ["app", "application", "server"]),
        ("server.py", ["app", "server", "application"]),
        ("asgi.py", ["app", "application"]),
    ]
    
    for filename, var_names in candidates:
        file_path = workspace_root / filename
        if file_path.exists():
            # Try to detect which variable is defined
            content = file_path.read_text()
            
            for var_name in var_names:
                # Look for variable assignments
                if f"{var_name} =" in content or f"{var_name}=" in content:
                    module_name = filename.replace(".py", "")
                    app_ref = f"{module_name}:{var_name}"
                    
                    if verbose:
                        print(f"✓ Found app: {app_ref}")
                    
                    return app_ref
    
    return None
