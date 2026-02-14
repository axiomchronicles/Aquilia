"""Production server command.

Starts an optimised uvicorn server using frozen artifacts (if available)
or the standard workspace app loader.  Multi-worker support is enabled
by default for production workloads.
"""

import os
import sys
from pathlib import Path

from ..utils.workspace import get_workspace_file


def serve_production(
    workers: int = 1,
    bind: str = '0.0.0.0:8000',
    verbose: bool = False,
) -> None:
    """
    Start production server.

    Args:
        workers: Number of workers
        bind: Bind address (host:port)
        verbose: Enable verbose output
    """
    try:
        import uvicorn
    except ImportError:
        raise ImportError(
            "uvicorn is required to run the production server.\n"
            "Install it with: pip install uvicorn\n"
            "Or with extras: pip install 'aquilia[server]'"
        )

    workspace_root = Path.cwd()
    ws_file = get_workspace_file(workspace_root)

    if not ws_file:
        raise ValueError("Not in an Aquilia workspace (workspace.py not found)")

    # Parse host:port from bind
    if ':' in bind:
        host, port_str = bind.rsplit(':', 1)
        port = int(port_str)
    else:
        host = bind
        port = 8000

    # Add workspace to path
    if str(workspace_root) not in sys.path:
        sys.path.insert(0, str(workspace_root))

    # Set env variables for production mode
    os.environ['AQUILIA_ENV'] = 'prod'
    os.environ['AQUILIA_WORKSPACE'] = str(workspace_root)

    # Use the same app loader as `aq run` (runtime/app.py)
    from .run import _create_workspace_app
    app_module = _create_workspace_app(workspace_root, mode='prod', verbose=verbose)

    if verbose:
        print(f"🚀 Starting Aquilia production server")
        print(f"  Bind:    {host}:{port}")
        print(f"  Workers: {workers}")
        print(f"  App:     {app_module}")
        print()

    uvicorn.run(
        app=app_module,
        host=host,
        port=port,
        workers=workers,
        reload=False,
        log_level="warning" if not verbose else "info",
        access_log=False,
    )
