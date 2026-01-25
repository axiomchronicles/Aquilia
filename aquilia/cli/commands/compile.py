"""Manifest compilation command."""

from pathlib import Path
from typing import Optional, List

from ..compilers import WorkspaceCompiler


def compile_workspace(
    output_dir: Optional[str] = None,
    watch: bool = False,
    verbose: bool = False,
) -> List[str]:
    """
    Compile manifests to artifacts.
    
    Args:
        output_dir: Output directory for artifacts
        watch: Watch for changes and recompile
        verbose: Enable verbose output
    
    Returns:
        List of generated artifact paths
    """
    workspace_root = Path.cwd()
    workspace_config = workspace_root / 'workspace.py'
    
    if not workspace_config.exists():
        raise ValueError("Not in an Aquilia workspace (workspace.py not found)")
    
    output = Path(output_dir) if output_dir else workspace_root / 'artifacts'
    output.mkdir(parents=True, exist_ok=True)
    
    compiler = WorkspaceCompiler(
        workspace_root=workspace_root,
        output_dir=output,
        verbose=verbose,
    )
    
    artifacts = compiler.compile()
    
    if watch:
        raise NotImplementedError("Watch mode not yet implemented")
    
    return [str(a.relative_to(workspace_root)) for a in artifacts]
