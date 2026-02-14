"""Workspace compiler - converts manifests to artifacts."""

from pathlib import Path
from typing import List, Any, Optional
import json
import importlib.util
import sys


class WorkspaceCompiler:
    """Compile workspace manifests to .crous artifacts."""
    
    def __init__(
        self,
        workspace_root: Path,
        output_dir: Path,
        verbose: bool = False,
    ):
        self.workspace_root = workspace_root
        self.output_dir = output_dir
        self.verbose = verbose

        # Ensure workspace root is on sys.path so module imports resolve
        ws_abs = str(self.workspace_root.resolve())
        if ws_abs not in sys.path:
            sys.path.insert(0, ws_abs)
    
    def _load_module_manifest(self, module_name: str) -> Optional[Any]:
        """Load manifest.py from module and return the manifest *instance*."""
        module_path = self.workspace_root / 'modules' / module_name
        manifest_path = module_path / 'manifest.py'
        
        if not manifest_path.exists():
            return None
        
        try:
            spec = importlib.util.spec_from_file_location(
                f"_compile_{module_name}_manifest", manifest_path
            )
            if not spec or not spec.loader:
                return None
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            
            # Convention: manifest = AppManifest(...)
            manifest_obj = getattr(module, 'manifest', None)
            if manifest_obj is not None:
                return manifest_obj

            # Fallback: look for any AppManifest instance or subclass
            from aquilia.manifest import AppManifest
            for name, obj in vars(module).items():
                if isinstance(obj, AppManifest):
                    return obj
                if isinstance(obj, type) and issubclass(obj, AppManifest) and obj is not AppManifest:
                    # Instantiate the class
                    try:
                        return obj()
                    except Exception:
                        return obj

            return None
        except Exception as exc:
            if self.verbose:
                print(f"  ⚠  Could not load manifest for '{module_name}': {exc}")
            return None

    def compile(self) -> List[Path]:
        """
        Compile workspace to artifacts.
        
        Returns:
            List of generated artifact paths
        """
        artifacts = []
        
        # Load workspace configuration
        workspace_file = self.workspace_root / 'workspace.py'
        if not workspace_file.exists():
             raise ValueError("workspace.py not found")
             
        workspace_content = workspace_file.read_text()
        import re
        
        # Extract workspace info
        name_match = re.search(r'Workspace\("([^"]+)"', workspace_content)
        name = name_match.group(1) if name_match else "aquilia-workspace"
        
        version_match = re.search(r'version="([^"]+)"', workspace_content)
        version = version_match.group(1) if version_match else "0.1.0"
        
        desc_match = re.search(r'description="([^"]+)"', workspace_content)
        description = desc_match.group(1) if desc_match else ""
        
        # Extract modules
        modules = re.findall(r'Module\("([^"]+)"', workspace_content)
        
        # Build a simple namespace to hold workspace data
        class _WorkspaceMeta:
            pass
            
        workspace_manifest = _WorkspaceMeta()
        workspace_manifest.name = name
        workspace_manifest.version = version
        workspace_manifest.description = description
        workspace_manifest.modules = modules
        workspace_manifest.runtime = {}
        workspace_manifest.integrations = {}

        # Compile workspace metadata
        artifacts.append(self._compile_workspace_metadata(workspace_manifest))
        
        # Compile registry (module catalog)
        artifacts.append(self._compile_registry(workspace_manifest))
        
        # Compile each module
        for module_name in workspace_manifest.modules:
            module_artifacts = self._compile_module(module_name)
            artifacts.extend(module_artifacts)
        
        # Compile routing table
        artifacts.append(self._compile_routes(workspace_manifest))
        
        # Compile DI graph
        artifacts.append(self._compile_di_graph(workspace_manifest))
        
        return artifacts
    
    def _compile_workspace_metadata(self, manifest) -> Path:
        """Compile workspace metadata to aquilia.crous."""
        artifact = {
            'type': 'workspace_metadata',
            'name': manifest.name,
            'version': manifest.version,
            'description': manifest.description,
            'modules': manifest.modules,
            'runtime': manifest.runtime,
            'integrations': manifest.integrations,
        }
        
        output_path = self.output_dir / 'aquilia.crous'
        self._write_artifact(output_path, artifact)
        return output_path
    
    def _compile_registry(self, manifest) -> Path:
        """Compile module registry to registry.crous."""
        modules = []
        
        for module_name in manifest.modules:
            module_manifest = self._load_module_manifest(module_name)
            
            if module_manifest:
                faults_cfg = getattr(module_manifest, 'faults', None)
                default_domain = 'GENERIC'
                if faults_cfg:
                    default_domain = getattr(faults_cfg, 'default_domain', 'GENERIC')

                modules.append({
                    'name': getattr(module_manifest, 'name', module_name),
                    'version': getattr(module_manifest, 'version', '0.1.0'),
                    'description': getattr(module_manifest, 'description', ''),
                    'fault_domain': default_domain,
                    'depends_on': getattr(module_manifest, 'depends_on', []),
                })
            else:
                modules.append({
                    'name': module_name,
                    'version': '0.1.0',
                    'description': '',
                    'fault_domain': 'GENERIC',
                    'depends_on': [],
                })
        
        artifact = {
            'type': 'registry',
            'modules': modules,
        }
        
        output_path = self.output_dir / 'registry.crous'
        self._write_artifact(output_path, artifact)
        return output_path
    
    def _compile_module(self, module_name: str) -> List[Path]:
        """Compile module to module-specific artifacts."""
        module_manifest = self._load_module_manifest(module_name)
        
        if not module_manifest:
            return []

        faults_cfg = getattr(module_manifest, 'faults', None)
        default_domain = 'GENERIC'
        if faults_cfg:
            default_domain = getattr(faults_cfg, 'default_domain', 'GENERIC')

        # Get services (list of strings or ServiceConfig objects)
        services_raw = getattr(module_manifest, 'services', []) or []
        services_serialized = []
        for s in services_raw:
            if isinstance(s, str):
                services_serialized.append(s)
            elif hasattr(s, 'to_dict'):
                services_serialized.append(s.to_dict())
            else:
                services_serialized.append(str(s))

        # Get controllers (list of strings)
        controllers_raw = getattr(module_manifest, 'controllers', []) or []
        controllers_serialized = []
        for c in controllers_raw:
            if isinstance(c, str):
                controllers_serialized.append(c)
            else:
                controllers_serialized.append(str(c))

        artifact = {
            'type': 'module',
            'name': getattr(module_manifest, 'name', module_name),
            'version': getattr(module_manifest, 'version', '0.1.0'),
            'description': getattr(module_manifest, 'description', ''),
            'route_prefix': getattr(module_manifest, 'route_prefix', '/'),
            'fault_domain': default_domain,
            'depends_on': getattr(module_manifest, 'depends_on', []),
            'services': services_serialized,
            'controllers': controllers_serialized,
        }
        
        output_path = self.output_dir / f'{module_name}.crous'
        self._write_artifact(output_path, artifact)
        
        return [output_path]
    
    def _compile_routes(self, manifest) -> Path:
        """Compile routing table to routes.crous."""
        routes = []
        
        for module_name in manifest.modules:
            module_manifest = self._load_module_manifest(module_name)
            
            if not module_manifest:
                continue

            route_prefix = getattr(module_manifest, 'route_prefix', f'/{module_name}')
            controllers = getattr(module_manifest, 'controllers', []) or []

            for ctrl_ref in controllers:
                if isinstance(ctrl_ref, str) and ':' in ctrl_ref:
                    cls_name = ctrl_ref.rsplit(':', 1)[1]
                else:
                    cls_name = str(ctrl_ref)
                routes.append({
                    'module': module_name,
                    'controller': cls_name,
                    'controller_path': ctrl_ref if isinstance(ctrl_ref, str) else str(ctrl_ref),
                    'prefix': route_prefix,
                })
        
        artifact = {
            'type': 'routes',
            'routes': routes,
        }
        
        output_path = self.output_dir / 'routes.crous'
        self._write_artifact(output_path, artifact)
        return output_path
    
    def _compile_di_graph(self, manifest) -> Path:
        """Compile DI graph to di.crous."""
        providers = []
        
        for module_name in manifest.modules:
            module_manifest = self._load_module_manifest(module_name)
            
            if not module_manifest:
                continue

            services_list = getattr(module_manifest, 'services', []) or []
            
            for svc in services_list:
                if isinstance(svc, str):
                    svc_name = svc.rsplit(':', 1)[-1] if ':' in svc else svc
                    providers.append({
                        'module': module_name,
                        'class': svc_name,
                        'class_path': svc,
                        'scope': 'app',
                    })
                elif hasattr(svc, 'class_path'):
                    scope = getattr(svc, 'scope', 'app')
                    scope_val = scope.value if hasattr(scope, 'value') else str(scope)
                    providers.append({
                        'module': module_name,
                        'class': svc.class_path.rsplit(':', 1)[-1] if ':' in svc.class_path else svc.class_path,
                        'class_path': svc.class_path,
                        'scope': scope_val,
                    })
        
        artifact = {
            'type': 'di_graph',
            'providers': providers,
        }
        
        output_path = self.output_dir / 'di.crous'
        self._write_artifact(output_path, artifact)
        return output_path
    
    def _write_artifact(self, path: Path, data: dict) -> None:
        """Write artifact to file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
