"""
Pages Module - Manifest

Showcases template and lifecycle configuration.
"""

from aquilia import AppManifest
from aquilia.manifest import LifecycleConfig, FeatureConfig

manifest = AppManifest(
    name="pages",
    version="0.1.0",
    description="HTML pages with templates, navigation, and lifecycle hooks",
    author="team@aquilia.dev",
    tags=["pages", "templates", "frontend"],

    services=[
        "modules.pages.services:NavigationService",
        "modules.pages.services:PageContentService",
    ],
    controllers=[
        "modules.pages.controllers:PagesController",
    ],

    route_prefix="/pages",
    base_path="modules.pages",

    features=[
        FeatureConfig(name="contact_form", enabled=True),
        FeatureConfig(name="dashboard", enabled=True),
        FeatureConfig(name="blog_pages", enabled=False),
    ],
)
