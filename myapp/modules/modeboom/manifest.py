"""
Modeboom module manifest.
"""

from aquilia.manifest import AppManifest
from .faults import MODEBOOM


class ModeboomManifest(AppManifest):
    """
    Manifest for modeboom module.
    """

    name = "modeboom"
    version = "0.1.0"
    description = "Modeboom module"

    route_prefix = "/modeboom"
    default_fault_domain = MODEBOOM

    depends_on = []

    # Controllers and Services are auto-discovered by default
    # but can be explicitly listed here:
    # controllers = []
    # services = []