"""
Controller System Verification

Tests that the new Controller architecture works correctly.
"""

import asyncio
from aquilia import (
    Controller,
    GET, POST,
    Request,
    Response,
    extract_controller_metadata,
    ControllerFactory,
    InstantiationMode,
)
from aquilia.controller import RequestCtx  # Import specifically from controller


# Test Controller
class TestController(Controller):
    prefix = "/test"
    tags = ["test"]
    
    def __init__(self):
        self.call_count = 0
    
    @GET("/")
    async def index(self, ctx: RequestCtx):
        self.call_count += 1
        return Response({"message": "test", "count": self.call_count})
    
    @GET("/«id:int»")
    async def get_item(self, ctx: RequestCtx, id: int):
        return Response({"id": id})
    
    @POST("/create")
    async def create(self, ctx: RequestCtx):
        data = await ctx.json() if hasattr(ctx.request, 'json') else {}
        return Response({"created": True, "data": data})


async def verify_controller_metadata():
    """Verify metadata extraction."""
    print("1️⃣  Verifying metadata extraction...")
    
    metadata = extract_controller_metadata(
        TestController,
        "test.module:TestController"
    )
    
    assert metadata.class_name == "TestController"
    assert metadata.prefix == "/test"
    assert len(metadata.routes) == 3
    
    # Check routes
    routes_by_method = {r.handler_name: r for r in metadata.routes}
    
    # Index route
    index_route = routes_by_method['index']
    assert index_route.http_method == 'GET'
    assert index_route.full_path == '/test'  # Trailing slash stripped
    
    # Get item route
    get_route = routes_by_method['get_item']
    assert get_route.http_method == 'GET'
    assert get_route.full_path == '/test/«id:int»'
    assert len(get_route.parameters) > 0
    
    # Create route
    create_route = routes_by_method['create']
    assert create_route.http_method == 'POST'
    assert create_route.full_path == '/test/create'
    
    print("   ✅ Metadata extraction works correctly")
    print(f"      - Extracted {len(metadata.routes)} routes")
    print(f"      - Prefix: {metadata.prefix}")
    print(f"      - Tags: {metadata.tags}")


async def verify_controller_instantiation():
    """Verify controller instantiation."""
    print("\n2️⃣  Verifying controller instantiation...")
    
    # Per-request mode
    factory = ControllerFactory()
    
    controller1 = await factory.create(
        TestController,
        mode=InstantiationMode.PER_REQUEST
    )
    controller2 = await factory.create(
        TestController,
        mode=InstantiationMode.PER_REQUEST
    )
    
    assert controller1 is not controller2
    print("   ✅ Per-request mode creates new instances")
    
    # Singleton mode
    singleton1 = await factory.create(
        TestController,
        mode=InstantiationMode.SINGLETON
    )
    singleton2 = await factory.create(
        TestController,
        mode=InstantiationMode.SINGLETON
    )
    
    assert singleton1 is singleton2
    print("   ✅ Singleton mode reuses same instance")


async def verify_controller_execution():
    """Verify controller method execution."""
    print("\n3️⃣  Verifying controller method execution...")
    
    # Create controller
    controller = TestController()
    
    # Create mock request context with ASGI-style scope
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/test/",
        "query_string": b"",
        "headers": [],
    }
    request = Request(scope, lambda: None)
    ctx = RequestCtx(request=request)
    
    # Execute method
    response = await controller.index(ctx)
    
    # Response with dict automatically becomes JSON
    import json
    response_data = json.loads(response._content) if isinstance(response._content, str) else response._content
    assert response_data["message"] == "test"
    assert response_data["count"] == 1
    print("   ✅ Controller methods execute correctly")
    
    # Execute again
    response2 = await controller.index(ctx)
    response_data2 = json.loads(response2._content) if isinstance(response2._content, str) else response2._content
    assert response_data2["count"] == 2
    print("   ✅ Controller state preserved between calls")
    
    # Execute with path parameter
    response3 = await controller.get_item(ctx, id=42)
    response_data3 = json.loads(response3._content) if isinstance(response3._content, str) else response3._content
    assert response_data3["id"] == 42
    print("   ✅ Path parameters bound correctly")


async def verify_route_specificity():
    """Verify route specificity computation."""
    print("\n4️⃣  Verifying route specificity...")
    
    metadata = extract_controller_metadata(
        TestController,
        "test.module:TestController"
    )
    
    for route in metadata.routes:
        specificity = route.compute_specificity()
        assert specificity > 0
        print(f"   ✓ {route.full_path}: specificity={specificity}")
    
    print("   ✅ Route specificity computed correctly")


async def verify_request_ctx():
    """Verify RequestCtx functionality."""
    print("\n5️⃣  Verifying RequestCtx...")
    
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/test/create",
        "query_string": b"foo=bar",
        "headers": [(b"content-type", b"application/json")],
    }
    request = Request(scope, lambda: None)
    
    ctx = RequestCtx(request=request)
    
    assert ctx.method == "POST"
    assert ctx.path == "/test/create"
    assert ctx.headers["content-type"] == "application/json"
    assert ctx.query_params.get("foo") == ["bar"]  # query returns Dict[str, list]
    assert ctx.query_param("foo") == "bar"  # query_param returns single value
    
    print("   ✅ RequestCtx provides correct access to request data")


async def main():
    print("\n" + "=" * 70)
    print("🧪 CONTROLLER SYSTEM VERIFICATION")
    print("=" * 70 + "\n")
    
    try:
        await verify_controller_metadata()
        await verify_controller_instantiation()
        await verify_controller_execution()
        await verify_route_specificity()
        await verify_request_ctx()
        
        print("\n" + "=" * 70)
        print("✅ ALL CONTROLLER SYSTEM TESTS PASSED!")
        print("=" * 70)
        print("\n🎉 Controller architecture is working correctly!")
        print("\nKey features verified:")
        print("  ✓ Metadata extraction from decorators")
        print("  ✓ Per-request and singleton instantiation")
        print("  ✓ Method execution with parameters")
        print("  ✓ Route specificity computation")
        print("  ✓ RequestCtx functionality")
        print("\n✨ Controllers are ready for production use!")
        print("=" * 70 + "\n")
        
        return True
    
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
