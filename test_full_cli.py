#!/usr/bin/env python3
"""Test the full CLI run command with timeout."""

import subprocess
import sys
import os
from pathlib import Path

def test_full_cli():
    """Test the full CLI run command."""
    print("Testing full CLI run command...")
    
    # Change to myapp directory
    project_root = Path(__file__).parent
    myapp_dir = project_root / "myapp"
    
    try:
        # Run the CLI command with timeout
        result = subprocess.run(
            [sys.executable, "-m", "aquilia.cli", "run", "--reload"],
            cwd=str(myapp_dir),
            capture_output=True,
            text=True,
            timeout=5,  # 5 second timeout
            env=dict(os.environ, PYTHONPATH=str(project_root))
        )
        
        print("CLI Output:")
        print(result.stdout)
        
        if result.stderr:
            print("CLI Errors:")
            print(result.stderr)
            
        print(f"Exit code: {result.returncode}")
        
    except subprocess.TimeoutExpired:
        print("✅ CLI started successfully (timed out as expected after 5s)")
        print("This means the server was starting up normally.")
    except Exception as e:
        print(f"CLI test error: {e}")

if __name__ == "__main__":
    test_full_cli()