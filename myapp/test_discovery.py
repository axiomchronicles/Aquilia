#!/usr/bin/env python3
"""Test discovery and workspace update."""

import sys
from pathlib import Path

workspace_root = Path.cwd()
sys.path.insert(0, str(workspace_root))
sys.path.insert(0, str(workspace_root.parent))

from aquilia.cli.commands.run import _discover_and_update_manifests

print("🔍 Auto-discovering controllers and services...")
print("=" * 70)
_discover_and_update_manifests(workspace_root, verbose=True)

print("\n✓ Complete")
