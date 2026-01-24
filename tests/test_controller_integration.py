"""
Integration test for Controller system with Aquilia architecture.

Tests full integration with:
- Pattern system for URL matching
- DI system for dependency injection
- Router for route matching
- Engine for execution
"""

import asyncio
from typing import Annotated

# Import from aquilia.controller (new system)
from aquilia.controller import (
    Controller,
    RequestCtx,
    GET,
    POST,
    ControllerCompiler,
    ControllerFactory,
    ControllerEngine,
    ControllerRouter,
)

# Import core Aquilia components
from aquilia.request import Request
from aquilia.response import Response
from aquilia.di import Container, Inject


# Example service for DI
class UserService:
    """Simple user service for testing DI."""
    
    def __init__(self):
        self.users = {
            1: {"id": 1, "name": "Alice"},
            2: {"id": 2, "name": "Bob"},
        }
    
    def get_user(self, user_id: int):
        return self.users.get(user_id)
    
    def list_users(self):
        return list(self.users.values())


# Example controller
class UsersController(Controller):
    """Test controller with DI and routes."""
    
    prefix = "/users"
    tags = ["users"]
    
    def __init__(self, service: Annotated[UserService, Inject()]):
        """Controller with DI injected service."""
        self.service = service
    
    @GET("/")
    async def list_users(self, ctx: RequestCtx):
        """List all users."""
        users = self.service.list_users()
        return Response.json({"users": users})
    
    @GET("/«id:int»")
    async def get_user(self, ctx: RequestCtx, id: int):
        """Get user by ID."""
        user = self.service.get_user(id)
        if user:
            return Response.json(user)
        else:
            return Response.json({"error": "User not found"}, status=404)
    
    @POST("/")
    async def create_user(self, ctx: RequestCtx):
        """Create a new user."""
        body = await ctx.json()
        return Response.json({"created": True, "data": body}, status=201)


class HealthController(Controller):
    """Simple health check controller."""
    
    prefix = "/health"
    
    @GET("/")
    async def health_check(self, ctx: RequestCtx):
        """Health check endpoint."""
        return Response.json({"status": "healthy"})


async def test_controller_compilation():
    """Test 1: Controller compilation with pattern integration."""
    print("\n" + "=" * 70)
    print("TEST 1: Controller Compilation")
    print("=" * 70)
    
    compiler = ControllerCompiler()
    
    # Compile UsersController
    compiled = compiler.compile_controller(UsersController)
    
    print(f"✅ Compiled {compiled.controller_class.__name__}")
    print(f"   Prefix: {compiled.metadata.prefix}")
    print(f"   Routes: {len(compiled.routes)}")
    
    for route in compiled.routes:
        print(f"      {route.http_method:6} {route.full_path:30} (specificity: {route.specificity})")
    
    # Check routes
    assert len(compiled.routes) == 3, f"Expected 3 routes, got {len(compiled.routes)}"
    assert compiled.metadata.prefix == "/users"
    
    print("✅ All assertions passed")


async def test_controller_routing():
    """Test 2: Controller routing with pattern matching."""
    print("\n" + "=" * 70)
    print("TEST 2: Controller Routing")
    print("=" * 70)
    
    # Setup
    compiler = ControllerCompiler()
    router = ControllerRouter()
    
    # Compile and add controllers
    users_compiled = compiler.compile_controller(UsersController)
    health_compiled = compiler.compile_controller(HealthController)
    
    router.add_controller(users_compiled)
    router.add_controller(health_compiled)
    router.initialize()
    
    print(f"✅ Router initialized with {len(router.compiled_controllers)} controllers")
    
    # Test matching
    test_cases = [
        ("GET", "/users", True, "list users"),
        ("GET", "/users/123", True, "get user by id"),
        ("POST", "/users", True, "create user"),
        ("GET", "/health", True, "health check"),
        ("GET", "/notfound", False, "non-existent route"),
        ("DELETE", "/users/123", False, "non-existent method"),
    ]
    
    for method, path, should_match, description in test_cases:
        match = await router.match(path, method)
        
        if should_match:
            assert match is not None, f"Expected match for {method} {path} ({description})"
            print(f"   ✅ {method:6} {path:20} -> {match.route.route_metadata.handler_name}")
        else:
            assert match is None, f"Expected no match for {method} {path} ({description})"
            print(f"   ✅ {method:6} {path:20} -> (no match)")
    
    print("✅ All routing tests passed")


async def test_controller_execution():
    """Test 3: Controller execution with DI integration."""
    print("\n" + "=" * 70)
    print("TEST 3: Controller Execution with DI")
    print("=" * 70)
    
    # Setup DI container
    container = Container(scope="app")
    
    # Register service using FactoryProvider
    from aquilia.di.providers import FactoryProvider
    service = UserService()
    
    provider = FactoryProvider(
        factory=lambda: service,
        scope="singleton",
        name="UserService",
    )
    container.register(provider)
    
    # Setup controller infrastructure
    factory = ControllerFactory(app_container=container)
    engine = ControllerEngine(factory=factory)
    compiler = ControllerCompiler()
    
    # Compile controller
    compiled = compiler.compile_controller(UsersController)
    list_route = compiled.routes[0]  # GET /users
    
    print(f"✅ Setup complete")
    print(f"   Route: {list_route.http_method} {list_route.full_path}")
    
    # Create mock request
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/users",
        "query_string": b"",
        "headers": [],
    }
    request = Request(scope, lambda: None)
    
    # Create request-scoped container
    request_container = container.create_request_scope()
    
    # Execute controller
    try:
        response = await engine.execute(
            route=list_route,
            request=request,
            path_params={},
            container=request_container,
        )
        
        print(f"✅ Execution successful")
        print(f"   Status: {response.status}")
        print(f"   Content-Type: {response.content_type}")
        
        # Parse response
        import json
        response_data = json.loads(response._content)
        
        print(f"   Users returned: {len(response_data['users'])}")
        
        assert response.status == 200
        assert "users" in response_data
        assert len(response_data["users"]) == 2
        
        print("✅ All execution tests passed")
    
    finally:
        await request_container.shutdown()


async def test_path_parameters():
    """Test 4: Path parameter extraction and type conversion."""
    print("\n" + "=" * 70)
    print("TEST 4: Path Parameters")
    print("=" * 70)
    
    # Setup
    container = Container(scope="app")
    
    # Register service using FactoryProvider
    from aquilia.di.providers import FactoryProvider
    service = UserService()
    
    provider = FactoryProvider(
        factory=lambda: service,
        scope="singleton",
        name="UserService",
    )
    container.register(provider)
    
    factory = ControllerFactory(app_container=container)
    engine = ControllerEngine(factory=factory)
    compiler = ControllerCompiler()
    
    # Compile and get route with parameter
    compiled = compiler.compile_controller(UsersController)
    get_route = next(r for r in compiled.routes if r.route_metadata.handler_name == "get_user")
    
    print(f"✅ Testing route: {get_route.http_method} {get_route.full_path}")
    
    # Create request for /users/1
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/users/1",
        "query_string": b"",
        "headers": [],
    }
    request = Request(scope, lambda: None)
    request_container = container.create_request_scope()
    
    try:
        # Execute with path params
        response = await engine.execute(
            route=get_route,
            request=request,
            path_params={"id": 1},  # Pattern system extracts and converts this
            container=request_container,
        )
        
        import json
        response_data = json.loads(response._content)
        
        print(f"✅ Response: {response_data}")
        
        assert response.status == 200
        assert response_data["id"] == 1
        assert response_data["name"] == "Alice"
        
        print("✅ Path parameter test passed")
    
    finally:
        await request_container.shutdown()


async def main():
    """Run all integration tests."""
    print("\n" + "=" * 70)
    print("🧪 CONTROLLER INTEGRATION TESTS")
    print("=" * 70)
    
    try:
        await test_controller_compilation()
        await test_controller_routing()
        await test_controller_execution()
        await test_path_parameters()
        
        print("\n" + "=" * 70)
        print("✅ ALL INTEGRATION TESTS PASSED!")
        print("=" * 70)
        print("\n🎉 Controller system fully integrated with Aquilia!\n")
        
        return 0
    
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
