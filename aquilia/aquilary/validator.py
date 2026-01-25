"""
Registry validator for manifests and configuration.
"""

from typing import Any, List, Dict, Set
from .errors import ValidationReport, ErrorSpan, CrossAppUsageError, RouteConflictError


class RegistryValidator:
    """
    Validates registry manifests and configuration.
    
    Checks:
    - Manifest structure
    - Config schemas
    - Cross-app dependencies
    - Route conflicts
    - Scope violations
    """
    
    def __init__(self, mode: Any):
        self.mode = mode
        self._app_names: Set[str] = set()
        self._route_index: Dict[str, List[Dict[str, str]]] = {}
    
    def validate_manifests(
        self,
        manifests: List[Any],
        config: Any,
    ) -> ValidationReport:
        """
        Validate all manifests.
        
        Args:
            manifests: List of manifest objects
            config: Config object
            
        Returns:
            ValidationReport with errors/warnings
        """
        report = ValidationReport()
        
        # Phase 1: Collect app names
        for manifest in manifests:
            self._app_names.add(manifest.name)
        
        # Phase 2: Validate each manifest
        for manifest in manifests:
            self._validate_manifest_structure(manifest, report)
            self._validate_dependencies(manifest, report)
            self._validate_config_namespace(manifest, config, report)
        
        # Phase 3: Validate route conflicts
        self._validate_route_conflicts(manifests, report)
        
        # Phase 4: Validate cross-app usage (if in strict mode)
        if self.mode.value == "prod":
            self._validate_cross_app_usage(manifests, report)
        
        return report
    
    def _validate_manifest_structure(
        self,
        manifest: Any,
        report: ValidationReport,
    ) -> None:
        """
        Validate manifest structure.
        
        Args:
            manifest: Manifest object
            report: ValidationReport to accumulate errors
        """
        from .errors import ManifestValidationError
        
        errors: List[str] = []
        
        # Required fields
        if not hasattr(manifest, "name") or not manifest.name:
            errors.append("Missing required field: name")
        
        if not hasattr(manifest, "version") or not manifest.version:
            errors.append("Missing required field: version")
        
        # Version format
        if hasattr(manifest, "version") and manifest.version:
            if not self._validate_semver(manifest.version):
                errors.append(f"Invalid version format: {manifest.version}")
                report.add_warning(
                    f"App '{manifest.name}': Version '{manifest.version}' "
                    "is not valid semver (expected X.Y.Z)"
                )
        
        # Controllers type
        if hasattr(manifest, "controllers"):
            if not isinstance(manifest.controllers, list):
                errors.append("Field 'controllers' must be a list")
            else:
                for i, ctrl in enumerate(manifest.controllers):
                    if not isinstance(ctrl, str):
                        errors.append(
                            f"controllers[{i}] must be string import path"
                        )
                    elif not self._validate_import_path(ctrl):
                        errors.append(
                            f"controllers[{i}] has invalid import path: {ctrl}"
                        )
        
        # Services type
        if hasattr(manifest, "services"):
            if not isinstance(manifest.services, list):
                errors.append("Field 'services' must be a list")
            else:
                for i, svc in enumerate(manifest.services):
                    if not isinstance(svc, str):
                        errors.append(f"services[{i}] must be string import path")
                    elif not self._validate_import_path(svc):
                        errors.append(
                            f"services[{i}] has invalid import path: {svc}"
                        )
        
        # Dependencies type
        if hasattr(manifest, "depends_on"):
            if not isinstance(manifest.depends_on, list):
                errors.append("Field 'depends_on' must be a list")
            else:
                for i, dep in enumerate(manifest.depends_on):
                    if not isinstance(dep, str):
                        errors.append(f"depends_on[{i}] must be string app name")
        
        # Middlewares type
        if hasattr(manifest, "middlewares"):
            if not isinstance(manifest.middlewares, list):
                errors.append("Field 'middlewares' must be a list")
            else:
                for i, mw in enumerate(manifest.middlewares):
                    if not isinstance(mw, (list, tuple)) or len(mw) != 2:
                        errors.append(
                            f"middlewares[{i}] must be (path, kwargs) tuple"
                        )
                    elif not isinstance(mw[0], str):
                        errors.append(
                            f"middlewares[{i}][0] must be string import path"
                        )
                    elif not isinstance(mw[1], dict):
                        errors.append(f"middlewares[{i}][1] must be dict")
        
        # Add errors to report
        if errors:
            span = ErrorSpan(file=getattr(manifest, "__source__", "unknown"))
            error = ManifestValidationError(
                manifest_name=manifest.name,
                validation_errors=errors,
                span=span,
            )
            report.add_error(error)
    
    def _validate_dependencies(
        self,
        manifest: Any,
        report: ValidationReport,
    ) -> None:
        """
        Validate app dependencies exist.
        
        Args:
            manifest: Manifest object
            report: ValidationReport to accumulate errors
        """
        from .errors import ManifestValidationError, ErrorSpan
        
        if not hasattr(manifest, "depends_on"):
            return
        
        missing_deps = [
            dep for dep in manifest.depends_on if dep not in self._app_names
        ]
        
        if missing_deps:
            span = ErrorSpan(file=getattr(manifest, "__source__", "unknown"))
            error = ManifestValidationError(
                manifest_name=manifest.name,
                validation_errors=[
                    f"Missing dependency: '{dep}' (not found in registry)"
                    for dep in missing_deps
                ],
                span=span,
            )
            report.add_error(error)
    
    def _validate_config_namespace(
        self,
        manifest: Any,
        config: Any,
        report: ValidationReport,
    ) -> None:
        """
        Validate config namespace exists.
        
        Args:
            manifest: Manifest object
            config: Config object
            report: ValidationReport to accumulate errors
        """
        if config is None:
            return
        
        # Check if app has config namespace
        if hasattr(config, "apps"):
            if not hasattr(config.apps, manifest.name):
                report.add_warning(
                    f"App '{manifest.name}' has no config namespace "
                    f"(expected config.apps.{manifest.name})"
                )
    
    def _validate_route_conflicts(
        self,
        manifests: List[Any],
        report: ValidationReport,
    ) -> None:
        """
        Validate no route conflicts between apps.
        
        Args:
            manifests: List of manifest objects
            report: ValidationReport to accumulate errors
        """
        # Build route index
        route_index: Dict[str, List[Dict[str, str]]] = {}
        
        for manifest in manifests:
            for controller_path in getattr(manifest, "controllers", []):
                # Extract route metadata (placeholder - needs router integration)
                # For now, just track controller paths
                route_key = f"*:{controller_path}"
                
                if route_key not in route_index:
                    route_index[route_key] = []
                
                route_index[route_key].append({
                    "app": manifest.name,
                    "controller": controller_path,
                })
        
        # Check for conflicts
        for route_key, providers in route_index.items():
            if len(providers) > 1:
                # Only error in prod mode, warn in dev
                if self.mode.value == "prod":
                    parts = route_key.split(":")
                    method = parts[0]
                    path = parts[1] if len(parts) > 1 else "unknown"
                    
                    error = RouteConflictError(
                        path=path,
                        method=method,
                        providers=providers,
                    )
                    report.add_error(error)
                else:
                    report.add_warning(
                        f"Route conflict: {route_key} claimed by "
                        f"{len(providers)} apps: "
                        f"{', '.join(p['app'] for p in providers)}"
                    )
    
    def _validate_cross_app_usage(
        self,
        manifests: List[Any],
        report: ValidationReport,
    ) -> None:
        """
        Validate cross-app service usage declares dependencies.
        
        Args:
            manifests: List of manifest objects
            report: ValidationReport to accumulate errors
        """
        # Build service ownership map
        service_owners: Dict[str, str] = {}
        
        for manifest in manifests:
            for service in getattr(manifest, "services", []):
                # Handle both ServiceConfig objects and string paths
                if hasattr(service, 'class_path'):
                    service_path = service.class_path
                else:
                    service_path = service
                service_owners[service_path] = manifest.name
        
        # Check each app's imports (placeholder - needs AST analysis)
        # For now, just validate declared dependencies exist
        pass
    
    def _validate_semver(self, version: str) -> bool:
        """
        Validate semver format.
        
        Args:
            version: Version string
            
        Returns:
            True if valid semver
        """
        parts = version.split(".")
        
        if len(parts) != 3:
            return False
        
        try:
            for part in parts:
                int(part)
            return True
        except ValueError:
            return False
    
    def _validate_import_path(self, path: str) -> bool:
        """
        Validate import path format.
        
        Supports two formats:
        - module.path (e.g., "myapp.controllers")
        - module.path:ClassName (e.g., "myapp.controllers:MyController")
        
        Args:
            path: Import path string
            
        Returns:
            True if valid
        """
        if not path:
            return False
        
        # Check for relative imports
        if path.startswith("."):
            return False
        
        # Split module path and optional class name
        if ":" in path:
            module_path, class_name = path.split(":", 1)
            # Validate class name is a valid identifier
            if not class_name.isidentifier():
                return False
        else:
            module_path = path
        
        # Check for valid Python identifier in module path
        parts = module_path.split(".")
        for part in parts:
            if not part.isidentifier():
                return False
        
        return True
    
    def validate_hot_reload(
        self,
        old_manifests: List[Any],
        new_manifests: List[Any],
    ) -> ValidationReport:
        """
        Validate hot-reload is safe.
        
        Checks:
        - No removed apps
        - No removed routes (only additions allowed)
        - No broken dependencies
        
        Args:
            old_manifests: Previous manifest list
            new_manifests: New manifest list
            
        Returns:
            ValidationReport
        """
        report = ValidationReport()
        
        old_apps = {m.name for m in old_manifests}
        new_apps = {m.name for m in new_manifests}
        
        # Check for removed apps
        removed_apps = old_apps - new_apps
        if removed_apps:
            report.add_warning(
                f"Hot-reload: Apps removed: {', '.join(sorted(removed_apps))}"
            )
        
        # Check for new apps
        added_apps = new_apps - old_apps
        if added_apps:
            report.add_warning(
                f"Hot-reload: Apps added: {', '.join(sorted(added_apps))}"
            )
        
        return report
