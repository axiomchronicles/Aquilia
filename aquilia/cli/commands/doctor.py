"""Workspace diagnostics command."""

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
    issues = []
    
    # Check for workspace manifest
    if not (workspace_root / 'aquilia.aq').exists():
        issues.append("Missing aquilia.aq (not in Aquilia workspace?)")
        return issues
    
    # Check for required directories
    required_dirs = ['modules', 'config']
    for dir_name in required_dirs:
        if not (workspace_root / dir_name).exists():
            issues.append(f"Missing required directory: {dir_name}/")
    
    # Check for config files
    config_dir = workspace_root / 'config'
    if config_dir.exists():
        required_configs = ['base.aq']
        for config in required_configs:
            if not (config_dir / config).exists():
                issues.append(f"Missing required config: config/{config}")
    
    # TODO: Add more diagnostic checks
    
    return issues
