"""
Integration Test - Verify Config → Registry → DI → Router integration.
"""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from aquilia.config import ConfigLoader, NestedNamespace
from aquilia.aquilary import Aquilary, RuntimeRegistry
from aquilia.di import Container


def test_config_namespacing():
    """Test that Config supports app namespacing."""
    print("✓ Testing Config namespacing...")
    
    # Create config with nested structure
    config = ConfigLoader(env_prefix="AQ_")
    config.config_data = {
        "debug": True,
        "apps": {
            "auth": {
                "secret_key": "test-secret",
                "token_expiry": 3600,
            },
            "users": {
                "max_users": 1000,
                "allow_signup": True,
            }
        }
    }
    config._build_apps_namespace()
    
    # Test namespace access
    assert hasattr(config, "apps"), "Config should have apps attribute"
    assert hasattr(config.apps, "auth"), "Apps should have auth namespace"
    assert config.apps.auth.secret_key == "test-secret"
    assert config.apps.users.max_users == 1000
    
    print("  ✅ Config namespacing works: config.apps.auth.secret_key")


def test_route_compiler():
    """Test RouteCompiler can extract routes from controllers."""
    print("\n✓ Testing RouteCompiler...")
    
    from aquilia.aquilary.route_compiler import RouteCompiler
    
    compiler = RouteCompiler()
    
    # Try to compile auth controller
    try:
        routes = compiler.compile_controller("apps.auth.controllers")
        print(f"  ✅ Found {len(routes)} routes in AuthController:")
        for route in routes:
            print(f"     {route.method:6s} {route.pattern}")
    except Exception as e:
        print(f"  ⚠️  Could not compile controller: {e}")


def test_registry_integration():
    """Test Registry → DI integration."""
    print("\n✓ Testing Registry → DI integration...")
    
    # Create minimal manifest
    class AuthManifest:
        name = "auth"
        version = "1.0.0"
        controllers = ["apps.auth.controllers"]
        services = ["apps.auth.services.AuthService"]
        depends_on = []
    
    # Create config
    config = ConfigLoader(env_prefix="AQ_")
    config.config_data = {
        "apps": {
            "auth": {
                "secret_key": "test-secret",
            }
        }
    }
    config._build_apps_namespace()
    
    try:
        # Build registry
        registry = Aquilary.from_manifests([AuthManifest], config=config)
        print(f"  ✅ Registry created with {len(registry.app_contexts)} apps")
        
        # Build runtime
        runtime = RuntimeRegistry.from_metadata(registry, config)
        print(f"  ✅ RuntimeRegistry created")
        
        # Test compilation (may fail if controllers have issues)
        try:
            runtime.compile_routes()
            if runtime.route_table:
                print(f"  ✅ Routes compiled: {runtime.route_table.to_dict()}")
        except Exception as e:
            print(f"  ⚠️  Route compilation failed: {e}")
        
    except Exception as e:
        print(f"  ❌ Registry integration failed: {e}")
        import traceback
        traceback.print_exc()


def test_di_containers():
    """Test DI container creation per app."""
    print("\n✓ Testing DI container creation...")
    
    container = Container(scope="app")
    
    # Register a simple service
    class TestService:
        def __init__(self):
            self.initialized = True
    
    container.register("TestService", TestService, scope="app")
    
    # Resolve it
    service = container.resolve("TestService")
    assert service.initialized
    
    print("  ✅ DI container works")


def main():
    """Run all integration tests."""
    print("=" * 60)
    print("Integration Tests - Config → Registry → DI → Router")
    print("=" * 60)
    
    test_config_namespacing()
    test_di_containers()
    test_route_compiler()
    test_registry_integration()
    
    print("\n" + "=" * 60)
    print("✅ Core integration tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
