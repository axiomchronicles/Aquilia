"""Workspace manifest parser."""

from pathlib import Path
from typing import Dict, List, Any
import yaml
from dataclasses import dataclass, field


@dataclass
class WorkspaceManifest:
    """Parsed workspace manifest (aquilia.aq)."""
    
    name: str
    version: str
    description: str = ""
    modules: List[str] = field(default_factory=list)
    runtime: Dict[str, Any] = field(default_factory=dict)
    integrations: Dict[str, Any] = field(default_factory=dict)
    _raw: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_file(cls, path: Path) -> 'WorkspaceManifest':
        """Load workspace manifest from file."""
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        
        workspace = data.get('workspace', {})
        modules_data = data.get('modules', [])
        
        # Extract module names
        modules = []
        if isinstance(modules_data, list):
            for module in modules_data:
                if isinstance(module, dict):
                    modules.append(module.get('name'))
                elif isinstance(module, str):
                    modules.append(module)
        
        return cls(
            name=workspace.get('name', ''),
            version=workspace.get('version', '0.1.0'),
            description=workspace.get('description', ''),
            modules=modules,
            runtime=data.get('runtime', {}),
            integrations=data.get('integrations', {}),
            _raw=data,
        )
    
    def add_module(self, name: str, config: Dict[str, Any]) -> None:
        """Add module to manifest."""
        if 'modules' not in self._raw:
            self._raw['modules'] = []
        
        # Ensure modules is a list
        if not isinstance(self._raw['modules'], list):
            self._raw['modules'] = []
        
        module_entry = {'name': name, **config}
        self._raw['modules'].append(module_entry)
        self.modules.append(name)
    
    def save(self, path: Path) -> None:
        """Save manifest to file."""
        with open(path, 'w') as f:
            yaml.dump(self._raw, f, default_flow_style=False, sort_keys=False)
