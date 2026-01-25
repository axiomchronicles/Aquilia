#!/usr/bin/env python3
"""Test if reload config is being applied correctly"""

import sys
from pathlib import Path

# Add current dir to path
sys.path.insert(0, str(Path.cwd()))

# Import and run with debug
from aquilia.cli.commands.run import _load_config

workspace_root = Path.cwd()
print(f"Workspace: {workspace_root}")
print()

# Test dev mode
print("=== DEV MODE ===")
config = _load_config(workspace_root, 'dev', verbose=True)
server_config = config.get('server', {})
reload_value = server_config.get('reload', 'NOT FOUND')
print(f"\nReload value from dev config: {reload_value}")
print(f"Type: {type(reload_value)}")
print(f"Is True?: {reload_value is True}")
print(f"Bool value: {bool(reload_value)}") 

# Test prod mode
print("\n=== PROD MODE ===")
config = _load_config(workspace_root, 'prod', verbose=True)
server_config = config.get('server', {})
reload_value = server_config.get('reload', 'NOT FOUND')
print(f"\nReload value from prod config: {reload_value}")
print(f"Type: {type(reload_value)}")
print(f"Bool value: {bool(reload_value)}")
