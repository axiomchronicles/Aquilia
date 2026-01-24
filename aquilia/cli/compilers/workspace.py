"""Workspace compiler - converts manifests to artifacts."""

from pathlib import Path
from typing import List
import json

from ..parsers import WorkspaceManifest, ModuleManifest


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
    
    def compile(self) -> List[Path]:
        """
        Compile workspace to artifacts.
        
        Returns:
            List of generated artifact paths
        """
        artifacts = []
        
        # Load workspace manifest
        workspace_manifest = WorkspaceManifest.from_file(
            self.workspace_root / 'aquilia.aq'
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
            module_path = self.workspace_root / 'modules' / module_name
            module_manifest_path = module_path / 'module.aq'
            
            if module_manifest_path.exists():
                module_manifest = ModuleManifest.from_file(module_manifest_path)
                modules.append({
                    'name': module_name,
                    'version': module_manifest.version,
                    'description': module_manifest.description,
                    'fault_domain': module_manifest.fault_domain,
                    'depends_on': module_manifest.depends_on,
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
        module_path = self.workspace_root / 'modules' / module_name
        module_manifest_path = module_path / 'module.aq'
        
        if not module_manifest_path.exists():
            return []
        
        module_manifest = ModuleManifest.from_file(module_manifest_path)
        
        # Compile module metadata
        artifact = {
            'type': 'module',
            'name': module_name,
            'version': module_manifest.version,
            'description': module_manifest.description,
            'route_prefix': module_manifest.route_prefix,
            'fault_domain': module_manifest.fault_domain,
            'depends_on': module_manifest.depends_on,
            'providers': module_manifest.providers,
            'routes': module_manifest.routes,
        }
        
        output_path = self.output_dir / f'{module_name}.crous'
        self._write_artifact(output_path, artifact)
        
        return [output_path]
    
    def _compile_routes(self, manifest: WorkspaceManifest) -> Path:
        """Compile routing table to routes.crous."""
        routes = []
        
        for module_name in manifest.modules:
            module_path = self.workspace_root / 'modules' / module_name
            module_manifest_path = module_path / 'module.aq'
            
            if module_manifest_path.exists():
                module_manifest = ModuleManifest.from_file(module_manifest_path)
                
                for route in module_manifest.routes:
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
            module_path = self.workspace_root / 'modules' / module_name
            module_manifest_path = module_path / 'module.aq'
            
            if module_manifest_path.exists():
                module_manifest = ModuleManifest.from_file(module_manifest_path)
                
                for provider in module_manifest.providers:
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
