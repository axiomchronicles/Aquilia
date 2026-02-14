"""
Sessions Module - Manifest
"""

from aquilia import AppManifest
from aquilia.manifest import FeatureConfig

manifest = AppManifest(
    name="sessions",
    version="0.1.0",
    description="Session management showcase: cart, preferences, wizard, and lifecycle",
    author="team@aquilia.dev",
    tags=["sessions", "cart", "preferences", "wizard"],

    services=[
        "modules.sessions.services:CartService",
        "modules.sessions.services:PreferencesService",
    ],
    controllers=[
        "modules.sessions.controllers:SessionsController",
    ],

    route_prefix="/sessions",
    base_path="modules.sessions",

    features=[
        FeatureConfig(name="shopping_cart", enabled=True),
        FeatureConfig(name="user_preferences", enabled=True),
        FeatureConfig(name="multi_step_wizard", enabled=True),
    ],
)
