"""Development server command."""

import sys
import os
import re
import importlib
from pathlib import Path
from typing import Optional, Dict, List, Set


def _validate_workspace_config(workspace_root: Path, verbose: bool = False) -> List[str]:
    """
    Validate that all modules registered in workspace.py/manifest.py actually exist.
    
    Checks:
    1. All registered module directories exist
    2. All manifest.py files can be found
    3. All controller/service imports are valid file paths
    4. No circular or missing dependencies
    
    Args:
        workspace_root: Path to workspace root
        verbose: Enable verbose output
        
    Returns:
        List of error messages (empty if validation passes)
    """
    errors = []
    
    try:
        # Check if workspace.py exists and is valid
        workspace_py = workspace_root / "workspace.py"
        if not workspace_py.exists():
            errors.append("workspace.py not found in workspace root")
            return errors
        
        # Read workspace.py to find registered modules
        try:
            workspace_content = workspace_py.read_text()
        except Exception as e:
            errors.append(f"Cannot read workspace.py: {str(e)[:60]}")
            return errors
        
        # Extract module names from workspace.py
        import re
        module_matches = re.findall(r'Module\("([^"]+)"', workspace_content)
        module_names = list(set(module_matches))  # Deduplicate

        # The "starter" pseudo-module lives in workspace root (starter.py),
        # not under modules/.  Skip it during validation — the server
        # auto-loads it via _load_starter_controller().
        module_names = [m for m in module_names if m != "starter"]
        
        if not module_names:
            # No modules registered - that's OK
            return errors
        
        modules_dir = workspace_root / "modules"
        if not modules_dir.exists():
            errors.append(f"modules directory not found at {modules_dir}")
            return errors
        
        # Validate each registered module
        for module_name in module_names:
            module_dir = modules_dir / module_name
            
            # Check if module directory exists
            if not module_dir.exists():
                errors.append(f"Module directory not found: modules/{module_name}")
                continue
            
            # Check if manifest.py exists
            manifest_path = module_dir / "manifest.py"
            if not manifest_path.exists():
                errors.append(f"Module manifest not found: modules/{module_name}/manifest.py")
                continue
            
            # Read manifest and validate imports
            try:
                manifest_content = manifest_path.read_text()
            except Exception as e:
                errors.append(f"Cannot read manifest for {module_name}: {str(e)[:50]}")
                continue
            
            # Extract controller and service imports (skip commented lines)
            # Format: "modules.mymodule.services:MymoduleService"
            imports = []
            for line in manifest_content.split('\n'):
                # Skip lines that are comments
                stripped = line.strip()
                if stripped.startswith('#'):
                    continue
                # Extract quoted strings with ':' pattern from this line
                line_imports = re.findall(r'"([^"]*:[\w]+)"', line)
                imports.extend(line_imports)
            
            # Validate each import can be resolved
            for import_path in imports:
                if ':' not in import_path:
                    continue
                
                module_path, class_name = import_path.split(':')
                
                # Convert module path to file path
                # Example: "modules.mymodule.services" -> "modules/mymodule/services.py"
                parts = module_path.split('.')
                
                # Skip 'modules' prefix and rebuild path starting from module_dir
                if parts[0] == 'modules' and len(parts) > 1:
                    parts = parts[1:]  # Remove 'modules' prefix
                
                # Skip module name itself (parts[0] is module_name)
                if parts and parts[0] == module_name:
                    parts = parts[1:]
                
                # Build file path
                try:
                    file_path = module_dir
                    for part in parts:
                        file_path = file_path / part
                    
                    file_path = file_path.with_suffix('.py')
                    
                    if not file_path.exists():
                        errors.append(
                            f"Import error in {module_name}: {import_path} "
                            f"(file not found: {file_path.relative_to(workspace_root)})"
                        )
                except Exception as e:
                    errors.append(
                        f"Cannot validate import {import_path} in {module_name}: {str(e)[:40]}"
                    )
    
    except Exception as e:
        errors.append(f"Unexpected error during validation: {str(e)[:60]}")
    
    return errors


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
    from aquilia.cli.discovery_utils import EnhancedDiscovery
    from pathlib import Path
    import sys
    
    workspace_root = Path(workspace_root)
    
    # Add workspace root to Python path for imports
    workspace_abs = workspace_root.resolve()
    if str(workspace_abs) not in sys.path:
        sys.path.insert(0, str(workspace_abs))
    
    modules_dir = workspace_root / "modules"
    if not modules_dir.exists():
        return
    
    discovery = EnhancedDiscovery(verbose=verbose)
    
    # Track discovery results
    total_controllers = 0
    total_services = 0
    modules_updated = 0
    
    # Discover all modules with manifest.py
    for module_dir in modules_dir.iterdir():
        if not module_dir.is_dir() or module_dir.name.startswith('_'):
            continue
        
        manifest_path = module_dir / "manifest.py"
        if not manifest_path.exists():
            continue
        
        module_name = module_dir.name
        base_package = f"modules.{module_name}"
        
        if verbose:
            print(f"\n  🔍 Discovering module: {module_name}")
        
        try:
            # Use enhanced discovery to get properly classified controllers, services, and socket controllers
            result = discovery.discover_module_controllers_and_services(
                base_package, module_name
            )
            # Handle both 2-tuple (legacy) and 3-tuple (new) return values
            if len(result) == 3:
                discovered_controllers, discovered_services, discovered_sockets = result
            else:
                discovered_controllers, discovered_services = result
                discovered_sockets = []
            
            if verbose:
                if discovered_controllers:
                    print(f"    ✅ Found {len(discovered_controllers)} controller(s)")
                if discovered_services:
                    print(f"    ✅ Found {len(discovered_services)} service(s)")
                if discovered_sockets:
                    print(f"    ✅ Found {len(discovered_sockets)} socket controller(s)")
            
            total_controllers += len(discovered_controllers)
            total_services += len(discovered_services)
            
            # Read manifest content
            try:
                manifest_content = manifest_path.read_text()
            except (OSError, IOError) as e:
                if verbose:
                    print(f"    ⚠️  Cannot read manifest: {str(e)[:60]}")
                continue
            
            # Clean and update manifest with properly classified items
            try:
                updated_content, services_added, controllers_added = discovery.clean_manifest_lists(
                    manifest_content,
                    discovered_controllers,
                    discovered_services,
                    module_dir=module_dir,  # Pass module path for validation
                    discovered_sockets=discovered_sockets,
                )
            except Exception as e:
                if verbose:
                    print(f"    ⚠️  Error cleaning manifest: {str(e)[:60]}")
                continue
            
            # Write updated manifest if there were changes
            if updated_content != manifest_content:
                try:
                    manifest_path.write_text(updated_content)
                    modules_updated += 1
                    if verbose:
                        total_changes = services_added + controllers_added
                        print(f"    ✅ Updated manifest: {services_added} service(s), {controllers_added} controller(s) added")
                except (OSError, IOError) as e:
                    if verbose:
                        print(f"    ⚠️  Cannot write manifest: {str(e)[:60]}")
            elif verbose:
                print(f"    ✓ Manifest already up-to-date")
                
        except Exception as e:
            if verbose:
                print(f"    ⚠️  Unexpected error processing {module_name}: {str(e)[:80]}")
    
    # After updating all manifests, update workspace.py with discovered configs
    try:
        from ..generators.workspace import WorkspaceGenerator
        
        generator = WorkspaceGenerator(
            name=workspace_root.name,
            path=workspace_root
        )
        
        # Re-discover with updated manifests to get all controllers/services
        discovered = generator._discover_modules()
        
        if discovered:
            workspace_py_path = workspace_root / "workspace.py"
            if workspace_py_path.exists():
                generator.update_workspace_config(workspace_py_path, discovered)
    
    except Exception as e:
        if verbose:
            print(f"⚠️  Failed to update workspace.py: {str(e)[:80]}")


def _discover_and_display_routes(workspace_root: Path, verbose: bool = False) -> None:
    """
    Discover all modules and their routes before starting server.
    
    Args:
        workspace_root: Path to workspace root
        verbose: Enable verbose output
    """
    from aquilia.cli.discovery_utils import EnhancedDiscovery
    from pathlib import Path
    import sys
    
    workspace_root = Path(workspace_root)
    
    # Add workspace root to path
    workspace_abs = workspace_root.resolve()
    if str(workspace_abs) not in sys.path:
        sys.path.insert(0, str(workspace_abs))
    
    modules_dir = workspace_root / "modules"
    if not modules_dir.exists():
        return
    
    discovery = EnhancedDiscovery(verbose=False)
    
    # Collect all discovered modules with their controllers and services
    discovered_modules = {}
    
    # Discover all modules with manifest.py
    for module_dir in modules_dir.iterdir():
        if not module_dir.is_dir() or module_dir.name.startswith('_'):
            continue
            
        manifest_path = module_dir / 'manifest.py'
        if not manifest_path.exists():
            continue
            
        module_name = module_dir.name
        base_package = f"modules.{module_name}"
        
        try:
            # Use enhanced discovery
            result = discovery.discover_module_controllers_and_services(
                base_package, module_name
            )
            # Handle both 2-tuple (legacy) and 3-tuple (new) return values
            if len(result) == 3:
                discovered_controllers, discovered_services, discovered_sockets = result
            else:
                discovered_controllers, discovered_services = result
                discovered_sockets = []
            
            # Extract metadata from manifest
            manifest_content = manifest_path.read_text()
            import re
            version = re.search(r'version="([^"]+)"', manifest_content)
            description = re.search(r'description="([^"]+)"', manifest_content)
            route_prefix = re.search(r'route_prefix="([^"]+)"', manifest_content)
            tags = re.findall(r'"([^"]+)"', re.search(r'tags=\[(.*?)\]', manifest_content).group(1) if re.search(r'tags=\[(.*?)\]', manifest_content) else '')
            
            discovered_modules[module_name] = {
                'name': module_name,
                'version': version.group(1) if version else '0.1.0',
                'description': description.group(1) if description else f'{module_name.capitalize()} module',
                'route_prefix': route_prefix.group(1) if route_prefix else f'/{module_name}',
                'tags': tags or [module_name, 'core'],
                'controllers_list': [c["path"] if isinstance(c, dict) else c for c in discovered_controllers],
                'services_list': [s["path"] if isinstance(s, dict) else s for s in discovered_services],
                'sockets_list': [
                    {'path': s['path'] if isinstance(s, dict) else s,
                     'namespace': s.get('metadata', {}).get('namespace', '') if isinstance(s, dict) else ''}
                    for s in discovered_sockets
                ],
                'controllers_count': len(discovered_controllers),
                'services_count': len(discovered_services),
                'sockets_count': len(discovered_sockets),
                'has_controllers': len(discovered_controllers) > 0,
                'has_services': len(discovered_services) > 0,
                'has_sockets': len(discovered_sockets) > 0,
            }
            
            if verbose:
                print(f"\n🔍 Enhanced discovery for module: {module_name}")
                if discovered_controllers:
                    print(f"  ✅ Found {len(discovered_controllers)} controller(s)")
                if discovered_services:
                    print(f"  ✅ Found {len(discovered_services)} service(s)")
            
        except Exception as e:
            if verbose:
                print(f"  ⚠️  Error discovering {module_name}: {str(e)[:80]}")
    
    if not discovered_modules:
        return
    
    # Now display the results
    from ..generators.workspace import WorkspaceGenerator
    
    try:
        generator = WorkspaceGenerator(
            name=workspace_root.name,
            path=workspace_root
        )
        
        sorted_names = generator._resolve_dependencies(discovered_modules)
        validation = generator._validate_modules(discovered_modules)
    except Exception:
        sorted_names = sorted(discovered_modules.keys())
        validation = {'valid': True, 'warnings': [], 'errors': []}
    
    print("\n📍 Discovered Routes & Modules")
    print("=" * 70)
    
    # Display module table with controller details
    print(f"\n{'Module':<20} {'Route Prefix':<25} {'Controllers':<12} {'Services':<10} {'Sockets':<10}")
    print(f"{'-'*20} {'-'*25} {'-'*12} {'-'*10} {'-'*10}")
    
    for mod_name in sorted_names:
        if mod_name not in discovered_modules:
            continue
        mod = discovered_modules[mod_name]
        route = mod['route_prefix']
        controllers_count = mod.get('controllers_count', 0)
        services_count = mod.get('services_count', 0)
        sockets_count = mod.get('sockets_count', 0)
        print(f"{mod_name:<20} {route:<25} {controllers_count:<12} {services_count:<10} {sockets_count:<10}")
    
    # Show detailed controller information
    total_controllers = sum(mod.get('controllers_count', 0) for mod in discovered_modules.values())
    if total_controllers > 0:
        print(f"\n🎯 Controller Details:")
        for mod_name in sorted_names:
            if mod_name not in discovered_modules:
                continue
            mod = discovered_modules[mod_name]
            controllers_list = mod.get('controllers_list', [])
            if controllers_list:
                print(f"  {mod_name}:")
                for controller in controllers_list:
                    # Extract controller class name
                    if ':' in controller:
                        controller_class = controller.split(':')[1]
                    else:
                        controller_class = controller.split('.')[-1]
                    print(f"    • {controller_class}")
    
    # Show WebSocket controller details
    total_sockets = sum(mod.get('sockets_count', 0) for mod in discovered_modules.values())
    if total_sockets > 0:
        print(f"\n🔌 WebSocket Controllers:")
        for mod_name in sorted_names:
            if mod_name not in discovered_modules:
                continue
            mod = discovered_modules[mod_name]
            sockets_list = mod.get('sockets_list', [])
            if sockets_list:
                print(f"  {mod_name}:")
                for sock in sockets_list:
                    sock_path = sock['path'] if isinstance(sock, dict) else sock
                    namespace = sock.get('namespace', '') if isinstance(sock, dict) else ''
                    if ':' in sock_path:
                        sock_class = sock_path.split(':')[1]
                    else:
                        sock_class = sock_path.split('.')[-1]
                    if namespace:
                        print(f"    ⚡ {sock_class} → {namespace}")
                    else:
                        print(f"    ⚡ {sock_class}")
    
    print()
    
    # Summary
    print(f"\n📊 Summary:")
    with_services = sum(1 for m in discovered_modules.values() if m['has_services'])
    with_controllers = sum(1 for m in discovered_modules.values() if m['has_controllers'])
    with_sockets = sum(1 for m in discovered_modules.values() if m.get('has_sockets', False))
    
    total_services = sum(m.get('services_count', 0) for m in discovered_modules.values())
    total_controllers = sum(m.get('controllers_count', 0) for m in discovered_modules.values())
    total_sockets = sum(m.get('sockets_count', 0) for m in discovered_modules.values())
    
    print(f"  Total Modules: {len(discovered_modules)}")
    print(f"  With Services: {with_services} ({total_services} total)")
    print(f"  With Controllers: {with_controllers} ({total_controllers} total)")
    if total_sockets > 0:
        print(f"  With Sockets: {with_sockets} ({total_sockets} total)")
    
    # Validation status
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
    
    # ===== AUTO-DISCOVER & UPDATE MANIFESTS FIRST =====
    # This must happen BEFORE creating the app so that workspace.py is up-to-date
    print("🔍 Auto-discovering controllers and services...")
    _discover_and_update_manifests(workspace_root, verbose)
    
    # VALIDATE WORKSPACE CONFIGURATION BEFORE PROCEEDING
    print("🔍 Validating workspace configuration...")
    validation_errors = _validate_workspace_config(workspace_root, verbose)
    if validation_errors:
        print("\n❌ Workspace validation failed! Fix these issues before starting the server:\n")
        for error in validation_errors:
            print(f"  ❌ {error}")
        print()
        return
    
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
    
    # Discover and display all routes before starting server
    _discover_and_display_routes(workspace_root, verbose)
    
    # Configure uvicorn
    uvicorn.run(
        app=app_module,
        host=host,
        port=port,
        reload=reload,
        reload_dirs=[str(workspace_root)] if reload else None,
        log_level="debug" if verbose else "info",
        access_log=True,
        use_colors=True,
    )
    
    # server = uvicorn.Server(config)
    # server.run()


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

    # The "starter" pseudo-module is loaded automatically by the server
    # via _load_starter_controller(); don't try to import it as a manifest.
    modules = [m for m in modules if m != "starter"]
    
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

# Determine registry mode from config
from aquilia.aquilary.core import RegistryMode
_mode_str = config.config_data.get("mode", "dev")
_registry_mode = RegistryMode(_mode_str) if _mode_str in ("dev", "prod", "test") else RegistryMode.DEV

# Create server with all module manifests
server = AquiliaServer(
    manifests=[{manifests_str}],
    config=config,
    mode=_registry_mode,
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
