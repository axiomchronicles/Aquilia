"""
Controller generator - Creates controller boilerplate.
"""

from pathlib import Path
from typing import Optional


CONTROLLER_TEMPLATE = '''"""
{description}
"""

from aquilia import Controller, GET, POST, PUT, DELETE, RequestCtx, Response


class {class_name}(Controller):
    """
    {description}
    
    Routes:
        GET {prefix}/ - List all {resource_plural}
        POST {prefix}/ - Create a {resource_singular}
        GET {prefix}/«id:int» - Get {resource_singular} by ID
        PUT {prefix}/«id:int» - Update {resource_singular} by ID
        DELETE {prefix}/«id:int» - Delete {resource_singular} by ID
    """
    
    prefix = "{prefix}"
    tags = ["{tag}"]
    
    # Uncomment for DI (services auto-registered from manifest):
    # def __init__(self, service: YourService):
    #     self.service = service
    
    @GET("/")
    async def list_{resource_plural}(self, ctx: RequestCtx):
        """List all {resource_plural}."""
        # TODO: Implement list logic
        return Response.json({{
            "{resource_plural}": [],
            "total": 0
        }})
    
    @POST("/")
    async def create_{resource_singular}(self, ctx: RequestCtx):
        """Create a new {resource_singular}."""
        data = await ctx.json()
        
        # TODO: Implement create logic
        return Response.json({{
            "id": 1,
            "created": True,
            "data": data
        }}, status=201)
    
    @GET("/«id:int»")
    async def get_{resource_singular}(self, ctx: RequestCtx, id: int):
        """Get {resource_singular} by ID."""
        # TODO: Implement get logic
        return Response.json({{
            "id": id,
            "name": "Example {resource_singular}"
        }})
    
    @PUT("/«id:int»")
    async def update_{resource_singular}(self, ctx: RequestCtx, id: int):
        """Update {resource_singular} by ID."""
        data = await ctx.json()
        
        # TODO: Implement update logic
        return Response.json({{
            "id": id,
            "updated": True,
            "data": data
        }})
    
    @DELETE("/«id:int»")
    async def delete_{resource_singular}(self, ctx: RequestCtx, id: int):
        """Delete {resource_singular} by ID."""
        # TODO: Implement delete logic
        return Response.json({{
            "id": id,
            "deleted": True
        }}, status=204)
'''


CONTROLLER_WITH_LIFECYCLE_TEMPLATE = '''"""
{description}

This controller includes lifecycle hooks for advanced request handling.
"""

from aquilia import Controller, GET, POST, PUT, DELETE, RequestCtx, Response


class {class_name}(Controller):
    """
    {description}
    
    Lifecycle Hooks:
        - on_startup(ctx): Called once when controller initializes
        - on_request(ctx): Called before each request
        - on_response(ctx, response): Called after each request
    
    Routes:
        GET {prefix}/ - List all {resource_plural}
        POST {prefix}/ - Create a {resource_singular}
        GET {prefix}/«id:int» - Get {resource_singular} by ID
        PUT {prefix}/«id:int» - Update {resource_singular} by ID
        DELETE {prefix}/«id:int» - Delete {resource_singular} by ID
    """
    
    prefix = "{prefix}"
    tags = ["{tag}"]
    
    # Uncomment for DI (services auto-registered from manifest):
    # def __init__(self, service: YourService):
    #     self.service = service
    
    async def on_startup(self, ctx: RequestCtx) -> None:
        """
        Called once when controller initializes.
        
        Use for one-time setup like opening connections or loading config.
        """
        # TODO: Add startup logic
        pass
    
    async def on_request(self, ctx: RequestCtx) -> None:
        """
        Called before each request is processed.
        
        Use for request-level setup like logging or validation.
        """
        # TODO: Add request preprocessing logic
        # Example: Log request
        # print(f"Request: {{ctx.method}} {{ctx.path}}")
        pass
    
    async def on_response(self, ctx: RequestCtx, response: Response) -> Response:
        """
        Called after each request is processed.
        
        Can modify the response before it's sent.
        """
        # TODO: Add response postprocessing logic
        # Example: Add custom header
        # response.headers["X-Processed-By"] = "{class_name}"
        return response
    
    @GET("/")
    async def list_{resource_plural}(self, ctx: RequestCtx):
        """List all {resource_plural}."""
        # TODO: Implement list logic
        return Response.json({{
            "{resource_plural}": [],
            "total": 0
        }})
    
    @POST("/")
    async def create_{resource_singular}(self, ctx: RequestCtx):
        """Create a new {resource_singular}."""
        data = await ctx.json()
        
        # TODO: Implement create logic
        return Response.json({{
            "id": 1,
            "created": True,
            "data": data
        }}, status=201)
    
    @GET("/«id:int»")
    async def get_{resource_singular}(self, ctx: RequestCtx, id: int):
        """Get {resource_singular} by ID."""
        # TODO: Implement get logic
        return Response.json({{
            "id": id,
            "name": "Example {resource_singular}"
        }})
    
    @PUT("/«id:int»")
    async def update_{resource_singular}(self, ctx: RequestCtx, id: int):
        """Update {resource_singular} by ID."""
        data = await ctx.json()
        
        # TODO: Implement update logic
        return Response.json({{
            "id": id,
            "updated": True,
            "data": data
        }})
    
    @DELETE("/«id:int»")
    async def delete_{resource_singular}(self, ctx: RequestCtx, id: int):
        """Delete {resource_singular} by ID."""
        # TODO: Implement delete logic
        return Response.json({{
            "id": id,
            "deleted": True
        }}, status=204)
'''


TEST_CONTROLLER_TEMPLATE = '''"""
{description}

Test/Demo controller with various endpoint examples.
"""

from aquilia import Controller, GET, POST, RequestCtx, Response


class {class_name}(Controller):
    """
    {description}
    
    Provides test endpoints for API verification and demonstration.
    """
    
    prefix = "{prefix}"
    tags = ["{tag}"]
    
    @GET("/hello")
    async def hello(self, ctx: RequestCtx):
        """Simple hello world test endpoint."""
        return Response.json({{
            "message": "Hello from Aquilia!",
            "status": "success",
            "controller": "{class_name}"
        }})
    
    @GET("/echo/«message:str»")
    async def echo(self, ctx: RequestCtx, message: str):
        """Echo back a message with path parameter."""
        return Response.json({{
            "echo": message,
            "length": len(message),
            "type": "path_param"
        }})
    
    @POST("/data")
    async def post_data(self, ctx: RequestCtx):
        """Test POST with JSON body."""
        try:
            data = await ctx.json()
            return Response.json({{
                "received": data,
                "keys": list(data.keys()) if isinstance(data, dict) else None,
                "status": "processed"
            }})
        except Exception as e:
            return Response.json({{
                "error": str(e),
                "status": "failed"
            }}, status=400)
    
    @GET("/status/«code:int»")
    async def status_code(self, ctx: RequestCtx, code: int):
        """Test different HTTP status codes."""
        messages = {{
            200: "OK",
            201: "Created",
            400: "Bad Request",
            404: "Not Found",
            500: "Internal Server Error"
        }}
        return Response.json({{
            "code": code,
            "message": messages.get(code, "Unknown Status")
        }}, status=code)
    
    @GET("/headers")
    async def headers(self, ctx: RequestCtx):
        """Test custom response headers."""
        response = Response.json({{
            "message": "Check the headers!",
            "custom_header": "X-Custom-Test"
        }})
        response.headers["X-Custom-Test"] = "Aquilia-Test-Value"
        response.headers["X-Request-ID"] = "test-12345"
        return response
    
    @GET("/health")
    async def health(self, ctx: RequestCtx):
        """Health check endpoint."""
        return Response.json({{
            "status": "healthy",
            "service": "{tag}",
            "controller": "{class_name}"
        }})
    
    @GET("/info")
    async def info(self, ctx: RequestCtx):
        """Get API info."""
        return Response.json({{
            "api": "Aquilia Test API",
            "version": "1.0.0",
            "endpoints": [
                "GET {prefix}/hello",
                "GET {prefix}/echo/{{message}}",
                "POST {prefix}/data",
                "GET {prefix}/status/{{code}}",
                "GET {prefix}/headers",
                "GET {prefix}/health",
                "GET {prefix}/info"
            ]
        }})
'''


SIMPLE_CONTROLLER_TEMPLATE = '''"""
{description}
"""

from aquilia import Controller, GET, RequestCtx, Response


class {class_name}(Controller):
    """
    {description}
    """
    
    prefix = "{prefix}"
    tags = ["{tag}"]
    
    @GET("/")
    async def index(self, ctx: RequestCtx):
        """Default route."""
        return Response.json({{
            "message": "Hello from {class_name}!",
            "path": ctx.path
        }})
'''


def generate_controller(
    name: str,
    output_dir: Path,
    prefix: Optional[str] = None,
    resource: Optional[str] = None,
    simple: bool = False,
    with_lifecycle: bool = False,
    test: bool = False,
) -> Path:
    """
    Generate a controller file.
    
    Args:
        name: Controller name (e.g., "Users", "Products")
        output_dir: Output directory
        prefix: URL prefix (default: auto-generated from name)
        resource: Resource name for CRUD (default: same as name)
        simple: Generate simple controller without CRUD
        with_lifecycle: Include lifecycle hooks (on_startup, on_request, on_response)
        test: Generate test/demo controller with example endpoints
    
    Returns:
        Path to generated file
    """
    # Normalize names
    class_name = f"{name}Controller" if not name.endswith("Controller") else name
    base_name = name.replace("Controller", "")
    
    # Generate prefix
    if prefix is None:
        prefix = f"/{base_name.lower()}"
    
    # Generate resource names
    if resource is None:
        resource = base_name.lower()
    
    resource_singular = resource.rstrip('s')
    resource_plural = resource if resource.endswith('s') else f"{resource}s"
    
    # Generate description
    if test:
        description = f"{base_name} Test Controller - Demo endpoints for testing"
    else:
        description = f"{base_name} Controller - Handles {resource_plural} endpoints"
    
    # Select template
    if test:
        content = TEST_CONTROLLER_TEMPLATE.format(
            class_name=class_name,
            prefix=prefix,
            tag=resource_plural,
            description=description,
        )
    elif simple:
        content = SIMPLE_CONTROLLER_TEMPLATE.format(
            class_name=class_name,
            prefix=prefix,
            tag=resource_plural,
            description=description,
        )
    elif with_lifecycle:
        content = CONTROLLER_WITH_LIFECYCLE_TEMPLATE.format(
            class_name=class_name,
            prefix=prefix,
            tag=resource_plural,
            description=description,
            resource_singular=resource_singular,
            resource_plural=resource_plural,
        )
    else:
        content = CONTROLLER_TEMPLATE.format(
            class_name=class_name,
            prefix=prefix,
            tag=resource_plural,
            description=description,
            resource_singular=resource_singular,
            resource_plural=resource_plural,
        )
    
    # Determine output path
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"{base_name.lower()}_controller.py"
    output_path = output_dir / filename
    
    # Write file
    output_path.write_text(content)
    
    return output_path


def generate_controller_manifest_entry(
    controller_path: str,
    class_name: str,
) -> str:
    """
    Generate manifest entry for controller.
    
    Args:
        controller_path: Module path (e.g., "app.controllers.users")
        class_name: Controller class name
    
    Returns:
        Manifest entry string
    """
    return f'        "{controller_path}:{class_name}",'


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python controller.py <name> [--simple] [--with-lifecycle] [--test] [--prefix PREFIX] [--resource RESOURCE]")
        print()
        print("Examples:")
        print("  python controller.py Users")
        print("  python controller.py Products --prefix /api/products")
        print("  python controller.py Health --simple")
        print("  python controller.py Admin --with-lifecycle")
        print("  python controller.py Test --test")
        sys.exit(1)
    
    name = sys.argv[1]
    simple = "--simple" in sys.argv
    with_lifecycle = "--with-lifecycle" in sys.argv
    test = "--test" in sys.argv
    
    prefix = None
    if "--prefix" in sys.argv:
        idx = sys.argv.index("--prefix")
        if idx + 1 < len(sys.argv):
            prefix = sys.argv[idx + 1]
    
    resource = None
    if "--resource" in sys.argv:
        idx = sys.argv.index("--resource")
        if idx + 1 < len(sys.argv):
            resource = sys.argv[idx + 1]
    
    output_path = generate_controller(
        name=name,
        output_dir=Path("."),
        prefix=prefix,
        resource=resource,
        simple=simple,
        with_lifecycle=with_lifecycle,
        test=test,
    )
    
    print(f"✅ Generated controller: {output_path}")
    print()
    print("Add to your manifest:")
    module_path = f"app.controllers.{name.lower()}"
    class_name = f"{name}Controller" if not name.endswith("Controller") else name
    entry = generate_controller_manifest_entry(module_path, class_name)
    print(f"    controllers=[")
    print(f"{entry}")
    print(f"    ]")

