"""
Controller generator - creates modern controller templates.
"""

from pathlib import Path
import textwrap


def generate_controller(
    name: str,
    output_dir: str = "controllers",
    prefix: str = None,
    resource: str = None,
    simple: bool = False,
    with_lifecycle: bool = False,
    test: bool = False,
) -> Path:
    """
    Generate a controller file.
    
    Args:
        name: Controller name
        output_dir: Output directory
        prefix: Route prefix
        resource: Resource name
        simple: Generate simple controller
        with_lifecycle: Include lifecycle hooks
        test: Generate test/demo controller
        
    Returns:
        Path to created controller file
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    file_path = output_path / f"{name.lower()}_controller.py"
    
    if test:
        content = _generate_test_controller(name, prefix or f"/{name.lower()}")
    elif simple:
        content = _generate_simple_controller(name, prefix or f"/{name.lower()}")
    elif with_lifecycle:
        content = _generate_lifecycle_controller(name, prefix or f"/{name.lower()}")
    else:
        content = _generate_standard_controller(name, prefix or f"/{name.lower()}", resource or name.lower())
    
    file_path.write_text(content)
    return file_path


def _generate_simple_controller(name: str, prefix: str) -> str:
    """Generate simple controller."""
    return textwrap.dedent(f'''
        """
        {name} Controller - Simple
        """
        
        from aquilia import Controller, GET
        
        
        class {name}Controller(Controller):
            """Simple {name} controller."""
            
            @GET("{prefix}")
            async def index(self, ctx):
                return {{"message": "Hello from {name}!"}}
    ''').strip() + "\n"


def _generate_standard_controller(name: str, prefix: str, resource: str) -> str:
    """Generate standard CRUD controller."""
    return textwrap.dedent(f'''
        """
        {name} Controller - Standard CRUD
        """
        
        from aquilia import Controller, GET, POST, PUT, DELETE
        from aquilia.sessions import Session
        
        
        class {name}Controller(Controller):
            """Standard CRUD controller for {resource}."""
            
            @GET("{prefix}")
            async def list(self, ctx):
                """List all {resource}s."""
                return {{"items": [], "total": 0}}
            
            @GET("{prefix}/{{id}}")
            async def get(self, ctx, id: str):
                """Get single {resource}."""
                return {{"id": id, "data": {{}}}}
            
            @POST("{prefix}")
            async def create(self, ctx):
                """Create new {resource}."""
                # body = await ctx.request.json()
                return {{"id": "new", "created": True}}
            
            @PUT("{prefix}/{{id}}")
            async def update(self, ctx, id: str):
                """Update {resource}."""
                # body = await ctx.request.json()
                return {{"id": id, "updated": True}}
            
            @DELETE("{prefix}/{{id}}")
            async def delete(self, ctx, id: str):
                """Delete {resource}."""
                return {{"id": id, "deleted": True}}
    ''').strip() + "\n"


def _generate_lifecycle_controller(name: str, prefix: str) -> str:
    """Generate controller with lifecycle hooks."""
    return textwrap.dedent(f'''
        """
        {name} Controller - With Lifecycle Hooks
        """
        
        from aquilia import Controller, GET
        
        
        class {name}Controller(Controller):
            """Controller with lifecycle hooks."""
            
            async def on_startup(self):
                """Called when controller is initialized."""
                print(f"{{self.__class__.__name__}} starting up...")
            
            async def on_request(self, ctx):
                """Called before each request."""
                print(f"Request: {{ctx.request.method}} {{ctx.request.path}}")
            
            async def on_response(self, ctx, response):
                """Called after each request."""
                print(f"Response: {{response}}")
                return response
            
            @GET("{prefix}")
            async def index(self, ctx):
                return {{"message": "Controller with lifecycle hooks"}}
    ''').strip() + "\n"


def _generate_test_controller(name: str, prefix: str) -> str:
    """Generate test/demo controller."""
    return textwrap.dedent(f'''
        """
        {name} Controller - Test/Demo
        """
        
        from aquilia import Controller, GET, POST
        from aquilia.sessions import Session, SessionPrincipal
        from aquilia.sessions.decorators import session, authenticated
        
        
        class {name}Controller(Controller):
            """Test/demo controller with various examples."""
            
            @GET("{prefix}")
            async def index(self, ctx):
                """Basic endpoint."""
                return {{"message": "Test controller", "status": "ok"}}
            
            @GET("{prefix}/echo")
            async def echo(self, ctx):
                """Echo request details."""
                return {{
                    "method": ctx.request.method,
                    "path": ctx.request.path,
                    "headers": dict(ctx.request.headers),
                }}
            
            @session.optional()
            @GET("{prefix}/session")
            async def session_test(self, ctx, session: Session | None):
                """Test session handling."""
                if session:
                    return {{"has_session": True, "session_id": str(session.id)}}
                return {{"has_session": False}}
            
            @authenticated
            @GET("{prefix}/protected")
            async def protected(self, ctx, user: SessionPrincipal):
                """Protected endpoint requiring authentication."""
                return {{"user_id": user.id, "authenticated": True}}
            
            @POST("{prefix}/data")
            async def post_data(self, ctx):
                """Test POST with body."""
                # body = await ctx.request.json()
                return {{"received": True, "echo": "data"}}
    ''').strip() + "\n"
