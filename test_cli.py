#!/usr/bin/env python3
"""Test the CLI run command discovery output."""

import sys
import os
from pathlib import Path

# Add Aquilia to path  
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "myapp"))
os.chdir(project_root / "myapp")

def test_cli_discovery():
    """Test the CLI discovery display."""
    print("Testing CLI discovery display...")
    
    try:
        from aquilia.cli.commands.run import _discover_and_display_routes
        
        workspace_root = Path(".")
        print(f"Testing discovery for workspace: {workspace_root.absolute()}")
        
        # Run the discovery and display
        _discover_and_display_routes(workspace_root, verbose=True)
        
        print("\n✅ CLI discovery test complete")
        
    except Exception as e:
        print(f"CLI test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_cli_discovery()