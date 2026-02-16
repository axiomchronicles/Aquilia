"""
Manifest management commands.

Provides commands to update and manage manifest.py files.
"""

import sys
import re
from pathlib import Path
import logging
from typing import List, Optional

from aquilia.utils.scanner import PackageScanner

logger = logging.getLogger("aquilia.cli.manifest")


def update_manifest(module_name: str, workspace_root: Path, check: bool = False, freeze: bool = False, verbose: bool = False):
    """
    Update manifest.py with auto-discovered resources.
    
    Args:
        module_name: Name of the module
        workspace_root: Root of the workspace
        check: If True, fail if updates are needed (dry-run)
        freeze: If True, disable auto-discovery after updating
        verbose: Verbose output
    """
    module_dir = workspace_root / "modules" / module_name
    manifest_path = module_dir / "manifest.py"
    
    if not manifest_path.exists():
        print(f"Error: Module '{module_name}' not found or missing manifest.py")
        sys.exit(1)
        
    if verbose:
        print(f"Scanning module '{module_name}'...")
    
    # 1. Scan for resources
    scanner = PackageScanner()
    base_package = f"modules.{module_name}"
    
    # Enhanced Controller Discovery with Intelligence
    all_controllers = []
    
    # Strategy 1: Standard subpackage scanning  
    standard_locations = [
        f"{base_package}.controllers",
        f"{base_package}.test_routes",
        f"{base_package}.handlers",
        f"{base_package}.views", 
        f"{base_package}.routes",
    ]
    
    for location in standard_locations:
        try:
            controllers = scanner.scan_package(
                location,
                predicate=lambda cls: (
                    cls.__name__.endswith("Controller") or
                    cls.__name__.endswith("Handler") or
                    cls.__name__.endswith("View") or
                    hasattr(cls, '__controller_routes__') or
                    hasattr(cls, 'prefix')
                ),
            )
            all_controllers.extend(controllers)
        except ImportError:
            pass
    
    # Strategy 2: Enhanced individual file scanning
    try:
        import importlib
        from pathlib import Path
        module_package = importlib.import_module(base_package)
        if hasattr(module_package, '__path__'):
            module_dir = Path(module_package.__path__[0])
            
            # Intelligent file pattern matching
            controller_patterns = [
                "*controller*.py", "*ctrl*.py", "*handler*.py", 
                "*view*.py", "*route*.py", "*api*.py",
                "*endpoint*.py", "*resource*.py"
            ]
            
            candidate_files = set()
            for pattern in controller_patterns:
                candidate_files.update(module_dir.glob(pattern))
            
            # Also scan all Python files (fallback)
            all_py_files = set(module_dir.glob("*.py"))
            other_files = all_py_files - candidate_files - {
                module_dir / "__init__.py", 
                module_dir / "manifest.py",
                module_dir / "config.py",
                module_dir / "settings.py"
            }
            
            for py_file in sorted(candidate_files) + sorted(other_files):
                if py_file.stem in ['__init__', 'manifest', 'config', 'settings']:
                    continue
                
                # Quick content analysis for performance
                try:
                    content = py_file.read_text(encoding='utf-8', errors='ignore')
                    if not ('Controller' in content or 'Handler' in content or 
                           'View' in content or 'class ' in content):
                        continue
                except Exception:
                    continue
                
                submodule_name = f"{base_package}.{py_file.stem}"
                try:
                    file_controllers = scanner.scan_package(
                        submodule_name,
                        predicate=lambda cls: (
                            cls.__name__.endswith("Controller") or
                            cls.__name__.endswith("Handler") or
                            cls.__name__.endswith("View") or
                            hasattr(cls, '__controller_routes__') or
                            hasattr(cls, 'prefix') or
                            # Duck typing for controller-like classes
                            any(hasattr(cls, method) for method in ['get', 'post', 'put', 'delete'])
                        ),
                    )
                    all_controllers.extend(file_controllers)
                except Exception:
                    pass
                    
    except Exception as scan_error:
        if verbose:
            print(f"  !  Enhanced individual file scan failed for {module_name}: {scan_error}")
    
    # Deduplicate results
    unique_controllers = {}
    for controller in all_controllers:
        key = f"{controller.__module__}:{controller.__name__}"
        if key not in unique_controllers:
            unique_controllers[key] = controller
    
    found_controllers = sorted(unique_controllers.keys())
    
    # Discover Services
    services = scanner.scan_package(
        f"{base_package}.services",
        predicate=lambda cls: cls.__name__.endswith("Service") or hasattr(cls, "__di_scope__"),
    )
    
    found_services = sorted(list(set(
        f"{s.__module__}:{s.__name__}" for s in services
    )))
    
    # 2. Parse Existing Manifest content to detect drift
    content = manifest_path.read_text()
    
    # Very crude extraction of what's currently there (for diffing in check mode)
    # Extract string arguments from register_controllers(...) calls
    # Matches: manifest.register_controllers(\n    "pkg.mod:Class",\n    ...
    # This is a best-effort check.
    
    def extract_registered(method: str) -> List[str]:
        # Regex to find all calls to the method
        # Matches: manifest.method(...)
        pattern = rf'manifest\.{method}\s*\((.*?)\)'
        matches = re.finditer(pattern, content, re.DOTALL)
        
        all_items = set()
        
        for match in matches:
            # Check if this specific call is commented out
            # We look at the start position of the match and check preceding lines for '#'
            start_pos = match.start()
            line_start = content.rfind('\n', 0, start_pos) + 1
            line_prefix = content[line_start:start_pos].strip()
            
            if line_prefix.startswith('#'):
                continue
                
            args_block = match.group(1)
            
            # Filter out comments INSIDE the args block
            cleaned_block = "\n".join(
                line for line in args_block.splitlines() 
                if not line.strip().startswith("#")
            )
            
            # Extract quoted strings
            items = re.findall(r'[\'"]([^\'"]+)[\'"]', cleaned_block)
            all_items.update(items)
            
        return sorted(list(all_items))

    existing_controllers = extract_registered("register_controllers")
    existing_services = extract_registered("register_services")
    
    # Compute Diff
    missing_controllers = set(found_controllers) - set(existing_controllers)
    extra_controllers = set(existing_controllers) - set(found_controllers)
    
    missing_services = set(found_services) - set(existing_services)
    extra_services = set(existing_services) - set(found_services)
    
    has_changes = bool(missing_controllers or extra_controllers or missing_services or extra_services)
    
    # Handle Check Mode
    if check:
        if not has_changes:
            print(f"✓ Manifest for '{module_name}' is in sync.")
            sys.exit(0)
        else:
            print(f"✗ Manifest for '{module_name}' is OUT OF SYNC.")
            if missing_controllers:
                print(f"  Missing Controllers: {', '.join(missing_controllers)}")
            if extra_controllers:
                print(f"  Extra Controllers:   {', '.join(extra_controllers)}")
            if missing_services:
                print(f"  Missing Services:    {', '.join(missing_services)}")
            if extra_services:
                print(f"  Extra Services:      {', '.join(extra_services)}")
            sys.exit(1)
    
    # Handle Update
    if not has_changes and not freeze:
        print(f"✓ Manifest for '{module_name}' is already up to date.")
        return

    # Helper to generate registration code
    def generate_block(method: str, items: List[str]) -> str:
        if not items:
            return ""
        items_str = ",\n    ".join([f'"{item}"' for item in items])
        return f"\nmanifest.{method}(\n    {items_str}\n)\n"

    sync_marker = "# --- Synced Resources (aq manifest update) ---"
    
    new_block = f"\n\n{sync_marker}"
    new_block += generate_block("register_controllers", found_controllers)
    new_block += generate_block("register_services", found_services)
    
    if sync_marker in content:
        # Replace existing block
        parts = content.split(sync_marker)
        content = parts[0].rstrip() + new_block
    else:
        # Append to end
        content = content.rstrip() + new_block
    
    # Handle Freeze Mode (Disable autodiscovery)
    if freeze:
        # Regex replace .auto_discover(True) -> .auto_discover(False)
        content = re.sub(r'\.auto_discover\(True\)', '.auto_discover(False)', content)
        # Also handle cases where it might be omitted or default (trickier, implying explicit True is best practice)
        print(f"❄️  Freezing manifest (auto_discover=False)")
        
    manifest_path.write_text(content)
    print(f"✓ Updated {manifest_path.relative_to(workspace_root)}")
    
    if missing_controllers or missing_services:
        print(f"  Synced {len(missing_controllers) + len(missing_services)} new items.")
