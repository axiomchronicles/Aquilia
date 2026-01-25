#!/usr/bin/env python3
"""Test the enhanced CLI with verbose output."""

import sys
import os
from pathlib import Path

# Add Aquilia to path  
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "myapp"))
os.chdir(project_root / "myapp")

def test_enhanced_cli_verbose():
    """Test the enhanced CLI discovery with verbose output."""
    print("🚀 Testing Enhanced CLI Discovery (Verbose Mode)")
    print("=" * 60)
    
    try:
        from aquilia.cli.commands.run import _discover_and_update_manifests
        
        workspace_root = Path(".")
        print(f"📂 Workspace: {workspace_root.absolute()}")
        
        print("\n🔍 Running Enhanced Discovery with Verbose Output...")
        print("-" * 50)
        
        # Run enhanced discovery with verbose output
        _discover_and_update_manifests(workspace_root, verbose=True)
        
        print("\n✅ Enhanced CLI Discovery Test Complete!")
        return True
        
    except Exception as e:
        print(f"❌ Enhanced CLI test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_enhanced_cli_verbose()
    if success:
        print("\n🎉 Enhanced CLI working with intelligent discovery!")
    else:
        print("\n⚠️ Enhanced CLI needs attention.")