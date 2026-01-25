"""Development server command."""

import sys
import os
from pathlib import Path
from typing import Optional


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
    modules = re.findall(r'(?m)^\s*\.module\(Module\("([^"]+)"\)', workspace_content)
    
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
config = ConfigLoader()

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
