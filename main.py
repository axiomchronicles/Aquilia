"""
Quick Test Server - Uses the modern controllers example
"""

from aquilia import AquiliaServer, AppManifest
from aquilia.config import ConfigLoader


# Import the demo manifest from examples
import sys
from pathlib import Path

# Add examples to path
sys.path.insert(0, str(Path(__file__).parent / "examples"))

try:
    from controllers_modern import DemoManifest
    
    # Create config
    config = ConfigLoader()
    config.config_data["debug"] = True
    config._build_apps_namespace()
    
    # Create server
    server = AquiliaServer(
        manifests=[DemoManifest],
        config=config,
    )
    
    # ASGI app
    app = server.app
    
    print("✓ Server configured successfully")
    print("Available routes:")
    print("  GET    /health       - Health check")
    print("  GET    /health/ping  - Ping")
    print("  GET    /users        - List users")
    print("  POST   /users        - Create user")
    print("  GET    /users/1      - Get user by ID")
    print("  PUT    /users/1      - Update user")
    print("  DELETE /users/1      - Delete user")
    print("  GET    /docs         - API docs")

except Exception as e:
    print(f"Warning: Could not load demo controllers: {e}")
    print("Creating minimal server instead...")
    
    # Minimal manifest
    class MinimalManifest(AppManifest):
        name = "minimal"
        version = "1.0.0"
        description = "Minimal demo"
        controllers = []
        services = []
    
    config = ConfigLoader()
    config.config_data["debug"] = True
    config.config_data["apps"] = {"minimal": {}}
    config._build_apps_namespace()
    
    server = AquiliaServer(
        manifests=[MinimalManifest],
        config=config,
    )
    
    app = server.app


if __name__ == "__main__":
    print("\nTo run: python -m aquilia.cli run")
    print("Or: uvicorn main:app --reload")
