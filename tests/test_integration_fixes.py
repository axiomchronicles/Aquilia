"""
Integration test for fixed systems.

Tests:
1. DI system with service injection
2. RuntimeRegistry route compilation
3. Handler DI injection
4. Request scope creation
5. Effect system initialization
"""

import pytest
import asyncio
from aquilia import AppManifest, flow, Response
from aquilia.di import service, Container
from aquilia.aquilary import Aquilary, RegistryMode
from aquilia.config import ConfigLoader
from aquilia.server import AquiliaServer
from aquilia.effects import EffectRegistry, EffectProvider


# Test service
@service(scope="app", name="TestService")
class TestService:
    """Test service for DI."""
    
    def __init__(self):
        self.initialized = True
    
    def get_data(self):
        return {"message": "Service works!"}


# Test controller
@flow("/test").GET
async def test_handler(service: TestService):
    """Test handler with DI injection."""
    return Response.json(service.get_data())


@flow("/health").GET
async def health():
    """Health check without DI."""
    return Response.json({"status": "ok"})


# Test manifest
class TestAppManifest(AppManifest):
    name = "test"
    version = "1.0.0"
    
    services = [
        "tests.test_integration_fixes:TestService",
    ]
    
    controllers = [
        "tests.test_integration_fixes:test_handler",
        "tests.test_integration_fixes:health",
    ]


@pytest.mark.asyncio
async def test_di_service_registration():
    """Test 1: DI service registration works."""
    config = ConfigLoader()
    
    # Build registry
    registry = Aquilary.from_manifests(
        manifests=[TestAppManifest],
        config=config,
        mode="test",
    )
    
    # Create server
    server = AquiliaServer(
        manifests=[TestAppManifest],
        config=config,
        mode=RegistryMode.TEST,
    )
    
    await server.startup()
    
    # Check DI containers created
    assert server.runtime is not None
    assert len(server.runtime.di_containers) > 0
    
    # Check service registered
    container = server.runtime.di_containers.get("test")
    assert container is not None
    
    # Should be able to resolve service
    service = await container.resolve_async("TestService")
    assert service is not None
    assert service.initialized is True
    
    await server.shutdown()


@pytest.mark.asyncio
async def test_route_compilation():
    """Test 2: Route compilation works."""
    config = ConfigLoader()
    
    server = AquiliaServer(
        manifests=[TestAppManifest],
        config=config,
        mode=RegistryMode.TEST,
    )
    
    await server.startup()
    
    # Check routes compiled
    assert server.runtime.router is not None
    assert server.router is not None
    
    # Check routes accessible
    routes = server.router.get_routes()
    assert len(routes) >= 2
    
    # Check specific routes exist
    route_patterns = [r['pattern'] for r in routes]
    assert '/test' in route_patterns
    assert '/health' in route_patterns
    
    await server.shutdown()


@pytest.mark.asyncio
async def test_handler_di_injection():
    """Test 3: Handler DI injection works."""
    config = ConfigLoader()
    
    server = AquiliaServer(
        manifests=[TestAppManifest],
        config=config,
        mode=RegistryMode.TEST,
    )
    
    await server.startup()
    
    # Route should be wrapped with DI
    match = server.router.match("/test", "GET")
    assert match is not None
    
    # Handler should be wrapped (not original function)
    handler = match.flow.handler_node.callable if match.flow.handler_node else None
    assert handler is not None
    
    # Handler should be able to execute (would inject service)
    # Note: Full execution test would require request object
    
    await server.shutdown()


@pytest.mark.asyncio
async def test_request_scope_creation():
    """Test 4: Request scope container creation works."""
    container = Container(scope="app")
    
    # Should be able to create request scope
    request_container = container.create_request_scope()
    
    assert request_container is not None
    assert request_container._scope == "request"
    assert request_container._parent == container
    
    # Should share provider registry
    assert request_container._providers is container._providers
    
    # But have separate cache
    assert request_container._cache is not container._cache


@pytest.mark.asyncio
async def test_effect_system_initialization():
    """Test 5: Effect system initialization works."""
    
    class TestEffectProvider(EffectProvider):
        def __init__(self):
            self.initialized = False
            self.finalized = False
        
        async def initialize(self):
            self.initialized = True
        
        async def acquire(self, mode=None):
            return {"mode": mode}
        
        async def release(self, resource, success=True):
            pass
        
        async def finalize(self):
            self.finalized = True
    
    registry = EffectRegistry()
    provider = TestEffectProvider()
    
    registry.register("TestEffect", provider)
    
    # Initialize all
    await registry.initialize_all()
    assert provider.initialized is True
    
    # Finalize all
    await registry.finalize_all()
    assert provider.finalized is True


@pytest.mark.asyncio
async def test_server_startup_sequence():
    """Test 6: Server startup sequence executes properly."""
    config = ConfigLoader()
    
    server = AquiliaServer(
        manifests=[TestAppManifest],
        config=config,
        mode=RegistryMode.TEST,
    )
    
    # Before startup
    assert server.runtime is not None
    assert not server.runtime._compiled
    
    # Startup
    await server.startup()
    
    # After startup - everything should be initialized
    assert server.runtime._compiled is True
    assert server.router is not None
    assert len(server.runtime.di_containers) > 0
    
    # Shutdown
    await server.shutdown()


def test_all_imports():
    """Test that all necessary imports work."""
    # New DI imports
    from aquilia.di import Container, service, inject
    from aquilia.di.providers import ClassProvider, ValueProvider
    
    # Aquilary imports
    from aquilia.aquilary import Aquilary, RuntimeRegistry
    from aquilia.aquilary.handler_wrapper import wrap_handler
    
    # Effect imports
    from aquilia.effects import EffectRegistry, Effect, EffectProvider
    
    # Server imports
    from aquilia.server import AquiliaServer
    from aquilia.engine import FlowEngine
    
    # All imports successful
    assert True


if __name__ == "__main__":
    # Run tests
    print("Running integration tests for fixed systems...")
    pytest.main([__file__, "-v", "-s"])
