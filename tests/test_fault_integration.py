import pytest
import asyncio
import uuid
import json
from typing import Any, Dict, Callable

from aquilia import AquiliaServer, Response
from aquilia.manifest import AppManifest, FaultHandlingConfig, FaultHandlerConfig
from aquilia.faults import (
    Fault, 
    FaultDomain, 
    FaultHandler, 
    FaultContext, 
    FaultResult, 
    Resolved,
)
from aquilia.controller import Controller, GET
from aquilia.request import Request
from aquilia.di import RequestCtx

# 1. Define custom fault domain
TEST_DOMAIN = FaultDomain("test_domain")

# 2. Define custom fault handler
class CustomFaultHandler(FaultHandler):
    async def handle(self, ctx: FaultContext) -> FaultResult:
        # Resolve fault with structured response
        return Resolved({
            "handled": True,
            "code": ctx.fault.code,
            "message": "Handler resolved: " + ctx.fault.message,
            "app": ctx.app
        })

# 3. Define faulty controller
class FaultyController(Controller):
    @GET("/trigger-fault")
    async def trigger(self, ctx):
        raise Fault(
            code="TEST_FAULT",
            message="This is a test fault",
            domain=TEST_DOMAIN
        )

# 4. Define app manifest with fault config
class FaultTestManifest(AppManifest):
    name = "fault_test_app"
    version = "1.0.0"
    controllers = ["tests.test_fault_integration:FaultyController"]
    faults = FaultHandlingConfig(
        handlers=[
            FaultHandlerConfig(
                domain="test_domain",
                handler_path="tests.test_fault_integration:CustomFaultHandler"
            )
        ]
    )

@pytest.fixture
async def server():
    # Instantiate server with test manifest
    server = AquiliaServer(manifests=[FaultTestManifest])
    await server.startup()
    yield server
    await server.shutdown()

@pytest.mark.asyncio
async def test_manifest_fault_handler_registration(server):
    """Verify that fault handler from manifest is registered and works."""
    # Check if handler is in registry
    registry = server.fault_engine.registry
    assert "fault_test_app" in registry._app
    assert len(registry._app["fault_test_app"]) == 1
    assert isinstance(registry._app["fault_test_app"][0], CustomFaultHandler)

@pytest.mark.asyncio
async def test_fault_middleware_interception(server):
    """Verify that FaultMiddleware catches fault and uses manifest handler."""
    app = server.app
    
    # Simulate a full request through the adapter
    from aquilia.asgi import ASGIAdapter
    
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/trigger-fault",
        "headers": [],
        "query_string": b"",
        "state": {}
    }
    
    # We need receive/send mocks
    async def receive():
        return {"type": "http.request", "body": b""}
        
    responses = []
    async def send(message):
        responses.append(message)
    
    await app(scope, receive, send)
    
    # Verify response
    assert any(resp["type"] == "http.response.start" and resp["status"] == 200 for resp in responses)
    
    body_msg = next(resp for resp in responses if resp["type"] == "http.response.body")
    body = json.loads(body_msg["body"].decode())
    
    assert body["handled"] is True
    assert body["code"] == "TEST_FAULT"
    assert "Handler resolved" in body["message"]
    assert body["app"] == "fault_test_app"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
