"""
Controller generator - Creates controller boilerplate.
"""

from pathlib import Path
from typing import Optional


CONTROLLER_TEMPLATE = '''"""
{description}
"""

from aquilia import Controller, GET, POST, PUT, DELETE, RequestCtx, Response
from typing import Annotated


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
    
    # Uncomment for DI:
    # def __init__(self, service: Annotated[YourService, Inject()]):
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
) -> Path:
    """
    Generate a controller file.
    
    Args:
        name: Controller name (e.g., "Users", "Products")
        output_dir: Output directory
        prefix: URL prefix (default: auto-generated from name)
        resource: Resource name for CRUD (default: same as name)
        simple: Generate simple controller without CRUD
    
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
    description = f"{base_name} Controller - Handles {resource_plural} endpoints"
    
    # Select template
    if simple:
        content = SIMPLE_CONTROLLER_TEMPLATE.format(
            class_name=class_name,
            prefix=prefix,
            tag=resource_plural,
            description=description,
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
        print("Usage: python controller.py <name> [--simple] [--prefix PREFIX] [--resource RESOURCE]")
        print()
        print("Examples:")
        print("  python controller.py Users")
        print("  python controller.py Products --prefix /api/products")
        print("  python controller.py Health --simple")
        sys.exit(1)
    
    name = sys.argv[1]
    simple = "--simple" in sys.argv
    
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
