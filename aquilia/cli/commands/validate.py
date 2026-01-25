"""Manifest validation command."""

from pathlib import Path
from typing import Optional
from dataclasses import dataclass
import importlib.util
import sys




@dataclass
class ValidationResult:
    """Result of manifest validation."""
    
    is_valid: bool
    module_count: int
    route_count: int
    provider_count: int
    faults: list[str]


def validate_workspace(
    strict: bool = False,
    module_filter: Optional[str] = None,
    verbose: bool = False,
) -> ValidationResult:
    """
    Validate workspace manifests.
    
    Args:
        strict: Enable strict (production-level) validation
        module_filter: Validate only specific module
        verbose: Enable verbose output
    
    Returns:
        ValidationResult with validation status and statistics
    """
    workspace_root = Path.cwd()
    workspace_root = Path.cwd()
    workspace_config = workspace_root / 'workspace.py'
    
    if not workspace_config.exists():
        raise ValueError("Not in an Aquilia workspace (workspace.py not found)")
    
    faults = []
    module_count = 0
    route_count = 0
    provider_count = 0
    
    # Load workspace modules
    try:
        workspace_content = workspace_config.read_text()
        import re
        # (?m) enables multiline mode, ^ matches start of line, \s* matches indentation
        modules = re.findall(r'(?m)^\s*\.module\(Module\("([^"]+)"\)', workspace_content)
    except Exception as e:
        faults.append(f"Invalid workspace configuration: {e}")
        return ValidationResult(
            is_valid=False,
            module_count=0,
            route_count=0,
            provider_count=0,
            faults=faults,
        )
    
    # Validate modules
    modules_to_validate = [module_filter] if module_filter else modules
    
    for module_name in modules_to_validate:
        module_path = workspace_root / 'modules' / module_name
        module_manifest_path = module_path / 'manifest.py'
        
        if not module_manifest_path.exists():
            faults.append(f"Module '{module_name}' missing manifest.py")
            continue
        
        try:

            # Import manifest.py dynamically
            spec = importlib.util.spec_from_file_location(f"{module_name}_manifest", module_manifest_path)
            if not spec or not spec.loader:
                raise ImportError(f"Could not load manifest from {module_manifest_path}")
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            
            # Find Manifest class
            manifest_class = getattr(module, f"{module_name.capitalize()}Manifest", None)
            if not manifest_class:
                # Try finding any subclass of AppManifest
                from aquilia.manifest import AppManifest
                for name, obj in vars(module).items():
                    if isinstance(obj, type) and issubclass(obj, AppManifest) and obj is not AppManifest:
                        manifest_class = obj
                        break
            
            if not manifest_class:
                raise ValueError(f"No AppManifest subclass found in {module_manifest_path}")
                
            module_count += 1
            # Routes/Providers logic would need to inspect the class attributes
            route_count += len(getattr(manifest_class, 'routes', []) or getattr(manifest_class, 'controllers', []))
            provider_count += len(getattr(manifest_class, 'providers', []) or getattr(manifest_class, 'services', []))
            
            # Validate module dependencies
            for dep in getattr(manifest_class, 'depends_on', []):
                if dep not in modules:
                    faults.append(f"Module '{module_name}' depends on non-existent module '{dep}'")
            
            # Strict validation
            if strict:
                # Check for required files
                required_files = ['flows.py', 'services.py', 'faults.py']
                for file in required_files:
                    if not (module_path / file).exists():
                        faults.append(f"Module '{module_name}' missing required file '{file}'")
        
        except Exception as e:
            faults.append(f"Invalid manifest in module '{module_name}': {e}")
    
    return ValidationResult(
        is_valid=len(faults) == 0,
        module_count=module_count,
        route_count=route_count,
        provider_count=provider_count,
        faults=faults,
    )
