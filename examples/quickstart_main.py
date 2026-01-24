"""
Simple Aquilia Application Entry Point

This is a basic example showing how to run an Aquilia server.
Customize this file for your application.
"""

from aquilia import AquiliaServer, AppManifest
from aquilia.config import ConfigLoader


# Define your app manifest
class DemoAppManifest(AppManifest):
    """Demo application manifest."""
    
    name = "demo"
    version = "1.0.0"
    description = "Demo Aquilia application"
    
    # Add your controllers here
    controllers = [
        # Example: "apps.users.controllers:UsersController",
    ]
    
    # Add your services here
    services = [
        # Example: "apps.users.services:UserService",
    ]


# Create config loader
config = ConfigLoader()
config.set("debug", True)  # Enable debug mode for development

# Create server with manifests
server = AquiliaServer(
    manifests=[DemoAppManifest],
    config=config,
)

# ASGI application for uvicorn
app = server.app


if __name__ == "__main__":
    print("=" * 70)
    print("🚀 Aquilia Development Server")
    print("=" * 70)
    print()
    print("To run this server:")
    print("  python -m aquilia.cli run")
    print()
    print("Or directly with uvicorn:")
    print("  uvicorn main:app --reload")
    print()
    print("=" * 70)
