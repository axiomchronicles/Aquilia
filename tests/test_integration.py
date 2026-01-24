"""
Integration tests for Aquilia server with Aquilary registry.
"""

import pytest
from aquilia import AppManifest, ConfigLoader, AquiliaServer
from aquilia.controller import Controller, GET
from aquilia.response import Response


@pytest.mark.asyncio
async def test_server_startup():
    """Test server startup with Aquilary."""
    manifest = AppManifest(
        name="test",
        version="1.0.0",
    )
    
    server = AquiliaServer(manifests=[manifest])
    
    await server.startup()
    await server.shutdown()


@pytest.mark.asyncio
async def test_request_handling():
    """Test handling a request with controller."""
    # Create test app
    manifest = AppManifest(
        name="test",
        version="1.0.0",
        controllers=["tests.test_integration:SampleController"],
    )
    
    server = AquiliaServer(manifests=[manifest])
    
    await server.startup()
    
    # Test that controller routes are registered
    routes = server.controller_router.get_routes()
    assert len(routes) > 0
    
    await server.shutdown()


class SampleController(Controller):
    """Sample controller for integration tests."""
    
    prefix = "/test"
    
    @GET("/")
    async def test_endpoint(self):
        return Response.json({"message": "test"})
    
    @GET("/«user_id:int»")
    async def test_param(self, user_id: int):
        return Response.json({"id": user_id})


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
