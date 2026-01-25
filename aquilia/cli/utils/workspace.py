"""
Utility functions for finding and loading workspace configuration.
"""

from pathlib import Path
from typing import Optional


def find_workspace_root(start_path: Optional[Path] = None) -> Optional[Path]:
    """
    Find the Aquilia workspace root by looking for workspace.py or aquilia.py.
    
    Searches upward from start_path (or cwd) until finding a workspace file.
    
    Args:
        start_path: Starting directory (defaults to cwd)
        
    Returns:
        Path to workspace root, or None if not found
    """
    if start_path is None:
        start_path = Path.cwd()
    
    current = start_path.resolve()
    
    # Search upward for workspace file
    while current != current.parent:
        # Check for workspace.py (new format)
        if (current / "workspace.py").exists():
            return current
        
        # Check for aquilia.py (alternative name)
        if (current / "aquilia.py").exists():
            return current
        
        # Check for aquilia.yaml (legacy format)
        if (current / "aquilia.yaml").exists():
            return current
        
        current = current.parent
    
    return None


def get_workspace_file(workspace_root: Path) -> Optional[Path]:
    """
    Get the workspace configuration file path.
    
    Checks for workspace.py, aquilia.py, or aquilia.yaml in that order.
    
    Args:
        workspace_root: Root directory of the workspace
        
    Returns:
        Path to workspace file, or None if not found
    """
    # Prefer workspace.py (new standard)
    if (workspace_root / "workspace.py").exists():
        return workspace_root / "workspace.py"
    
    # Fall back to aquilia.py
    if (workspace_root / "aquilia.py").exists():
        return workspace_root / "aquilia.py"
    
    # Legacy: aquilia.yaml
    if (workspace_root / "aquilia.yaml").exists():
        return workspace_root / "aquilia.yaml"
    
    return None


def is_python_workspace(workspace_root: Path) -> bool:
    """Check if workspace uses Python format (workspace.py or aquilia.py)."""
    return (
        (workspace_root / "workspace.py").exists() or
        (workspace_root / "aquilia.py").exists()
    )


def is_yaml_workspace(workspace_root: Path) -> bool:
    """Check if workspace uses YAML format (aquilia.yaml)."""
    return (workspace_root / "aquilia.yaml").exists()
