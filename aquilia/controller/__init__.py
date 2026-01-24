"""
Aquilia Controller System

First-class Controller architecture for Aquilia.
Replaces function-based @flow handlers with class-based Controllers.

Key Features:
- Manifest-first: Controllers declared in module.aq
- DI-first: Constructor and method parameter injection
- Pipeline-first: Class-level and method-level pipelines
- Static-first: Metadata extracted at compile time
- Zero import-time side effects

Example:
    from aquilia import Controller, GET, POST, Inject
    from typing import Annotated
    
    class UsersController(Controller):
        prefix = "/users"
        pipeline = [Auth.guard()]
        
        def __init__(self, repo: Annotated[UserRepo, Inject(tag="repo")]):
            self.repo = repo
        
        @GET("/")
        async def list(self, ctx):
            return self.repo.list_all()
        
        @GET("/«id:int»")
        async def retrieve(self, ctx, id: int):
            return self.repo.get(id)
"""

from .base import Controller, RequestCtx
from .decorators import (
    GET, POST, PUT, PATCH, DELETE,
    HEAD, OPTIONS, WS,
    route,
)
from .metadata import (
    ControllerMetadata,
    RouteMetadata,
    ParameterMetadata,
    extract_controller_metadata,
)
from .factory import (
    ControllerFactory,
    InstantiationMode,
)
from .engine import ControllerEngine
from .compiler import (
    ControllerCompiler,
    CompiledRoute,
    CompiledController,
)
from .router import ControllerRouter

__all__ = [
    # Base
    "Controller",
    "RequestCtx",
    
    # Decorators
    "GET", "POST", "PUT", "PATCH", "DELETE",
    "HEAD", "OPTIONS", "WS",
    "route",
    
    # Metadata
    "ControllerMetadata",
    "RouteMetadata",
    "ParameterMetadata",
    "extract_controller_metadata",
    
    # Factory
    "ControllerFactory",
    "InstantiationMode",
    
    # Engine
    "ControllerEngine",
    
    # Compilation
    "ControllerCompiler",
    "CompiledRoute",
    "CompiledController",
    
    # Routing
    "ControllerRouter",
]
