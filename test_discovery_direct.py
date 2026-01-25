#!/usr/bin/env python3
"""Test discovery module directly."""

import sys
from pathlib import Path

# Add workspace to path
workspace = Path("/Users/kuroyami/PyProjects/Aquilia/myapp")
sys.path.insert(0, str(workspace))
sys.path.insert(0, str(workspace.parent))

from aquilia.cli.discovery_utils import EnhancedDiscovery

discovery = EnhancedDiscovery(verbose=True)

print("Testing enhanced discovery...\n")

# Test module discovery
controllers, services = discovery.discover_module_controllers_and_services(
    "modules.mymodule",
    "mymodule"
)

print(f"\n✓ Discovered {len(controllers)} controller(s)")
for ctrl in controllers:
    print(f"  - {ctrl}")

print(f"\n✓ Discovered {len(services)} service(s)")
for svc in services:
    print(f"  - {svc}")
