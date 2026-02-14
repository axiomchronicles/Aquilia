"""Legacy project migration command.

Scans a Django-style / flat-file project layout and converts it to
the Aquilia workspace structure:
  - Detects app directories with views.py / urls.py
  - Creates modules/ with manifest.py for each detected app
  - Generates workspace.py with discovered modules
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass
class MigrationResult:
    """Result of migration operation."""
    changes: list[str] = field(default_factory=list)


def migrate_legacy(
    dry_run: bool = False,
    verbose: bool = False,
) -> MigrationResult:
    """
    Migrate from Django-style layout to Aquilia workspace.

    Looks for directories containing views.py / urls.py and treats them
    as candidate modules.

    Args:
        dry_run: Preview migration without making changes
        verbose: Enable verbose output

    Returns:
        MigrationResult with list of changes
    """
    workspace_root = Path.cwd()
    result = MigrationResult()

    # Detect candidate apps (directories with views.py or urls.py)
    candidates: List[Path] = []
    for child in sorted(workspace_root.iterdir()):
        if not child.is_dir() or child.name.startswith(('.', '_')):
            continue
        if child.name in ('modules', 'config', 'runtime', 'artifacts', 'env', 'venv', 'node_modules'):
            continue
        if (child / 'views.py').exists() or (child / 'urls.py').exists():
            candidates.append(child)

    if not candidates:
        result.changes.append("No Django-style app directories detected (no views.py/urls.py found)")
        return result

    # Ensure modules/ directory
    modules_dir = workspace_root / 'modules'
    if not modules_dir.exists():
        result.changes.append(f"Create directory: modules/")
        if not dry_run:
            modules_dir.mkdir(parents=True, exist_ok=True)

    module_names: List[str] = []

    for app_dir in candidates:
        app_name = app_dir.name
        mod_dir = modules_dir / app_name
        module_names.append(app_name)

        result.changes.append(f"Migrate app '{app_name}' → modules/{app_name}/")

        if dry_run:
            result.changes.append(f"  Would create modules/{app_name}/manifest.py")
            result.changes.append(f"  Would create modules/{app_name}/__init__.py")
            if (app_dir / 'views.py').exists():
                result.changes.append(f"  Would create modules/{app_name}/controllers.py  (from views.py)")
            if (app_dir / 'models.py').exists():
                result.changes.append(f"  Would create modules/{app_name}/services.py  (from models.py)")
            continue

        mod_dir.mkdir(parents=True, exist_ok=True)

        # Generate minimal manifest
        manifest_content = (
            f'"""Manifest for {app_name} (migrated from legacy layout)."""\n\n'
            f'from aquilia import AppManifest\n\n'
            f'manifest = AppManifest(\n'
            f'    name="{app_name}",\n'
            f'    version="0.1.0",\n'
            f'    description="{app_name.capitalize()} module (migrated)",\n'
            f'    route_prefix="/{app_name}",\n'
            f'    controllers=[],\n'
            f'    services=[],\n'
            f'    depends_on=[],\n'
            f')\n'
        )
        (mod_dir / 'manifest.py').write_text(manifest_content)
        result.changes.append(f"  Created modules/{app_name}/manifest.py")

        # __init__.py
        (mod_dir / '__init__.py').write_text(
            f'"""{app_name.capitalize()} module (migrated)."""\n'
        )
        result.changes.append(f"  Created modules/{app_name}/__init__.py")

        # Stub controllers from views.py
        if (app_dir / 'views.py').exists():
            ctrl_content = (
                f'"""\n{app_name.capitalize()} controllers (migrated from views.py).\n"""\n\n'
                f'from aquilia import Controller, GET\n\n\n'
                f'class {app_name.capitalize()}Controller(Controller):\n'
                f'    """Migrated controller for {app_name}."""\n\n'
                f'    @GET("/")\n'
                f'    async def index(self, ctx):\n'
                f'        return {{"message": "Migrated {app_name}"}}\n'
            )
            (mod_dir / 'controllers.py').write_text(ctrl_content)
            result.changes.append(f"  Created modules/{app_name}/controllers.py")

        # Stub services from models.py
        if (app_dir / 'models.py').exists():
            svc_content = (
                f'"""\n{app_name.capitalize()} services (migrated from models.py).\n"""\n\n\n'
                f'class {app_name.capitalize()}Service:\n'
                f'    """Migrated service for {app_name}."""\n'
                f'    pass\n'
            )
            (mod_dir / 'services.py').write_text(svc_content)
            result.changes.append(f"  Created modules/{app_name}/services.py")

        # Stub faults
        faults_content = (
            f'"""\n{app_name.capitalize()} fault definitions.\n"""\n\n'
            f'from aquilia.faults import Fault\n\n\n'
            f'class {app_name.capitalize()}NotFoundFault(Fault):\n'
            f'    domain = "{app_name.upper()}"\n'
            f'    code = "NOT_FOUND"\n'
            f'    message = "{app_name.capitalize()} resource not found"\n'
        )
        (mod_dir / 'faults.py').write_text(faults_content)
        result.changes.append(f"  Created modules/{app_name}/faults.py")

    # Generate workspace.py if it doesn't exist
    ws_file = workspace_root / 'workspace.py'
    if not ws_file.exists() and not dry_run and module_names:
        module_lines = '\n'.join(
            f'    .module(Module("{m}").route_prefix("/{m}"))'
            for m in module_names
        )
        ws_content = (
            '"""Aquilia workspace (migrated from legacy layout)."""\n\n'
            'from aquilia import Workspace, Module, Integration\n\n\n'
            'workspace = (\n'
            f'    Workspace("{workspace_root.name}", version="0.1.0")\n'
            f'{module_lines}\n'
            '    .integrate(Integration.di(auto_wire=True))\n'
            '    .integrate(Integration.routing(strict_matching=True))\n'
            '    .integrate(Integration.fault_handling(default_strategy="propagate"))\n'
            ')\n'
        )
        ws_file.write_text(ws_content)
        result.changes.append(f"Created workspace.py with {len(module_names)} module(s)")
    elif dry_run and not ws_file.exists() and module_names:
        result.changes.append(f"Would create workspace.py with {len(module_names)} module(s)")

    return result
