"""
Aquilia Discovery - Component auto-discovery subsystem.

This module provides the discovery layer for Aquilia, re-exporting
the core discovery capabilities from aquilary and utils:

- PackageScanner: Scans packages for controllers, services, socket controllers
- RuntimeRegistry.perform_autodiscovery: Executes the full discovery pipeline

Discovery is integrated into the Aquilary registry system.
Controllers, services, and socket controllers are discovered automatically
during ``server.startup()`` via ``RuntimeRegistry.perform_autodiscovery()``.

Usage:
    Discovery happens automatically. To customize, configure your manifests
    or use the CLI discovery commands (``aq discover``).

Re-exports:
    - PackageScanner from aquilia.utils.scanner
    - perform_autodiscovery from aquilia.aquilary.core.RuntimeRegistry
"""

from aquilia.utils.scanner import PackageScanner

__all__ = [
    "PackageScanner",
]
