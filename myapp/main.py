"""
Aquilia Workspace Configuration
==============================

Main entry point for the Aquilia workspace.
This file is automatically imported by the CLI.
"""

import sys
from pathlib import Path

# Add workspace root to path
workspace_root = Path(__file__).parent
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

from aquilia import AquiliaServer
from aquilia.config import ConfigLoader
from modules.mymodule.manifest import manifest as mymodule_manifest

# Create configuration
config = ConfigLoader.load(paths=["workspace.py"])

# Merge config data directly
config.config_data["debug"] = True
config.config_data["mode"] = "dev"

# Initialize apps config for each module
config.config_data["apps"] = {}
config.config_data["apps"]["mymodule"] = {}

# Build the apps namespace (required by Aquilary)
config._build_apps_namespace()

# Create server with all module manifests
server = AquiliaServer(
    manifests=[mymodule_manifest],
    config=config,
)

# ASGI application
app = server.app