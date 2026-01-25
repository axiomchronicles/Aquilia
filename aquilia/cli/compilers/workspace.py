"""Workspace compiler - converts manifests to artifacts."""

from pathlib import Path
from typing import List, Any
import json
import importlib.util
import sys

from ..parsers import WorkspaceManifest


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
    
    def _load_module_manifest(self, module_name: str) -> Any:
        """Load manifest.py from module."""
        module_path = self.workspace_root / 'modules' / module_name
        manifest_path = module_path / 'manifest.py'
        
        if not manifest_path.exists():
            return None
        
        try:
            # Import manifest.py dynamically
            spec = importlib.util.spec_from_file_location(f"{module_name}_manifest", manifest_path)
            if not spec or not spec.loader:
                return None
            
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
            
            return manifest_class
        except Exception:
            return None

    def compile(self) -> List[Path]:
        """
        Compile workspace to artifacts.
        
        Returns:
            List of generated artifact paths
        """
        artifacts = []
        
        # Load workspace manifest
        workspace_manifest = WorkspaceManifest.from_file(
            self.workspace_root / 'aquilia.yaml'
        )
        
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
    
    def _compile_workspace_metadata(self, manifest: WorkspaceManifest) -> Path:
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
    
    def _compile_registry(self, manifest: WorkspaceManifest) -> Path:
        """Compile module registry to registry.crous."""
        modules = []
        
        for module_name in manifest.modules:
            module_manifest = self._load_module_manifest(module_name)
            
            if module_manifest:
                modules.append({
                    'name': module_name,
                    'version': getattr(module_manifest, 'version', '0.1.0'),
                    'description': getattr(module_manifest, 'description', ''),
                    'fault_domain': getattr(module_manifest, 'default_fault_domain', 'GENERIC'),
                    'depends_on': getattr(module_manifest, 'depends_on', []),
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
        
        # Compile module metadata
        artifact = {
            'type': 'module',
            'name': module_name,
            'version': getattr(module_manifest, 'version', '0.1.0'),
            'description': getattr(module_manifest, 'description', ''),
            'route_prefix': getattr(module_manifest, 'route_prefix', '/'),
            'fault_domain': getattr(module_manifest, 'default_fault_domain', 'GENERIC'),
            'depends_on': getattr(module_manifest, 'depends_on', []),
            'providers': getattr(module_manifest, 'providers', []) or getattr(module_manifest, 'services', []),
            'routes': getattr(module_manifest, 'routes', []) or getattr(module_manifest, 'controllers', []),
        }
        
        output_path = self.output_dir / f'{module_name}.crous'
        self._write_artifact(output_path, artifact)
        
        return [output_path]
    
    def _compile_routes(self, manifest: WorkspaceManifest) -> Path:
        """Compile routing table to routes.crous."""
        routes = []
        
        for module_name in manifest.modules:
            module_manifest = self._load_module_manifest(module_name)
            
            if module_manifest:
                # Need to inspect routes from compiled code or manifest list
                # Inspecting metadata only
                routes_list = getattr(module_manifest, 'routes', [])
                if not routes_list:
                    # If controllers are listed, we can't easily extract routes without compiling controllers
                    # This is a static compiler limitation
                    pass
                
                for route in routes_list:
                    routes.append({
                        'module': module_name,
                        'path': route.get('path', '/'),
                        'handler': route.get('handler'),
                        'method': route.get('method', 'GET'),
                    })
        
        artifact = {
            'type': 'routes',
            'routes': routes,
        }
        
        output_path = self.output_dir / 'routes.crous'
        self._write_artifact(output_path, artifact)
        return output_path
    
    def _compile_di_graph(self, manifest: WorkspaceManifest) -> Path:
        """Compile DI graph to di.crous."""
        providers = []
        
        for module_name in manifest.modules:
            module_manifest = self._load_module_manifest(module_name)
            
            if module_manifest:
                providers_list = getattr(module_manifest, 'providers', []) 
                # Also handle 'services' list which are strings
                
                for provider in providers_list:
                    providers.append({
                        'module': module_name,
                        'class': provider.get('class'),
                        'scope': provider.get('scope', 'singleton'),
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
