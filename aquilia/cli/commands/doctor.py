"""Workspace diagnostics command.

Performs comprehensive health checks on the Aquilia workspace:
  - Workspace file presence
  - Required directories
  - Config files
  - Module structure validation
  - Manifest loadability
  - Controller / service import validation
  - Dependency resolution
"""

import re
import sys
import importlib.util
from pathlib import Path
from typing import List


def diagnose_workspace(verbose: bool = False) -> List[str]:
    """
    Diagnose workspace issues.

    Args:
        verbose: Enable verbose output

    Returns:
        List of issues found
    """
    workspace_root = Path.cwd()
    issues: List[str] = []

    # ── 1. Workspace file ────────────────────────────────────────────────
    from ..utils.workspace import get_workspace_file
    ws_file = get_workspace_file(workspace_root)
    if not ws_file:
        issues.append("Missing workspace.py or aquilia.yaml (not in Aquilia workspace?)")
        return issues

    if verbose:
        print(f"  ✓ Workspace file: {ws_file.name}")

    # ── 2. Required directories ──────────────────────────────────────────
    for dir_name in ('modules', 'config'):
        if not (workspace_root / dir_name).exists():
            issues.append(f"Missing required directory: {dir_name}/")

    # ── 3. Config files ──────────────────────────────────────────────────
    config_dir = workspace_root / 'config'
    if config_dir.exists():
        if not (config_dir / 'base.yaml').exists():
            issues.append("Missing required config: config/base.yaml")
    else:
        issues.append("Missing config/ directory")

    # ── 4. Extract registered modules ────────────────────────────────────
    try:
        ws_content = ws_file.read_text()
        registered_modules = re.findall(r'Module\("([^"]+)"', ws_content)
    except Exception as e:
        issues.append(f"Cannot read workspace file: {e}")
        return issues

    if not registered_modules:
        issues.append("No modules registered in workspace configuration")
        return issues

    if verbose:
        print(f"  ✓ Registered modules: {', '.join(registered_modules)}")

    # ── 5. Module-level checks ───────────────────────────────────────────
    modules_dir = workspace_root / 'modules'
    if not modules_dir.exists():
        return issues

    # Add workspace to path for import checks
    ws_abs = str(workspace_root.resolve())
    if ws_abs not in sys.path:
        sys.path.insert(0, ws_abs)

    for mod_name in registered_modules:
        mod_dir = modules_dir / mod_name

        # 5a. Directory exists?
        if not mod_dir.exists():
            issues.append(f"Module '{mod_name}' directory not found: modules/{mod_name}/")
            continue

        # 5b. manifest.py exists?
        manifest_path = mod_dir / 'manifest.py'
        if not manifest_path.exists():
            issues.append(f"Module '{mod_name}' missing manifest.py")
            continue

        # 5c. manifest.py loadable?
        manifest_obj = None
        try:
            spec = importlib.util.spec_from_file_location(
                f"_doctor_{mod_name}_manifest", manifest_path
            )
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                sys.modules[spec.name] = mod
                spec.loader.exec_module(mod)

                manifest_obj = getattr(mod, 'manifest', None)
                if manifest_obj is None:
                    from aquilia.manifest import AppManifest
                    for _n, obj in vars(mod).items():
                        if isinstance(obj, AppManifest):
                            manifest_obj = obj
                            break

            if manifest_obj is None:
                issues.append(f"Module '{mod_name}' manifest.py has no 'manifest' instance")
                continue

            if verbose:
                print(f"  ✓ Module '{mod_name}' manifest loaded")

        except Exception as e:
            issues.append(f"Module '{mod_name}' manifest.py import error: {str(e)[:80]}")
            continue

        # 5d. Validate controller references
        controllers = getattr(manifest_obj, 'controllers', []) or []
        for ctrl_ref in controllers:
            if not isinstance(ctrl_ref, str) or ':' not in ctrl_ref:
                continue
            mod_path, cls_name = ctrl_ref.rsplit(':', 1)
            parts = mod_path.split('.')
            if parts[0] == 'modules' and len(parts) > 1:
                file_parts = parts[1:]
                file_path = modules_dir.parent / 'modules'
                for p in file_parts:
                    file_path = file_path / p
                file_path = file_path.with_suffix('.py')
                if not file_path.exists():
                    # Could be a package
                    pkg_path = file_path.with_suffix('') / '__init__.py'
                    if not pkg_path.exists():
                        issues.append(
                            f"Module '{mod_name}' controller reference not found: {ctrl_ref} "
                            f"(expected {file_path.relative_to(workspace_root)})"
                        )

        # 5e. Validate service references
        services = getattr(manifest_obj, 'services', []) or []
        for svc_ref in services:
            if not isinstance(svc_ref, str) or ':' not in svc_ref:
                continue
            mod_path, cls_name = svc_ref.rsplit(':', 1)
            parts = mod_path.split('.')
            if parts[0] == 'modules' and len(parts) > 1:
                file_parts = parts[1:]
                file_path = modules_dir.parent / 'modules'
                for p in file_parts:
                    file_path = file_path / p
                file_path = file_path.with_suffix('.py')
                if not file_path.exists():
                    pkg_path = file_path.with_suffix('') / '__init__.py'
                    if not pkg_path.exists():
                        issues.append(
                            f"Module '{mod_name}' service reference not found: {svc_ref} "
                            f"(expected {file_path.relative_to(workspace_root)})"
                        )

        # 5f. Dependency check
        depends_on = getattr(manifest_obj, 'depends_on', []) or []
        for dep in depends_on:
            if dep not in registered_modules:
                issues.append(
                    f"Module '{mod_name}' depends on '{dep}' which is not registered"
                )

    if verbose and not issues:
        print("  ✓ All checks passed")

    return issues
