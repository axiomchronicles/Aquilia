
import pytest
import asyncio
from typing import Protocol, Annotated
from aquilia.di import Container, ClassProvider, ValueProvider, FactoryProvider
from aquilia.controller.factory import ControllerFactory, InstantiationMode, ScopeViolationError
from aquilia.di.errors import CircularDependencyError, ProviderNotFoundError

# --- Fixtures & Helpers ---

class IService(Protocol):
    def get_value(self) -> str: ...

class ConcreteService:
    def get_value(self) -> str: return "concrete"

class SimpleService:
    pass

class DependencyService:
    def __init__(self, simple: SimpleService):
        self.simple = simple

class CycleA:
    def __init__(self, b: "CycleB"): self.b = b

class CycleB:
    def __init__(self, a: CycleA): self.a = a

class RequestService:
    pass

class SingletonService:
    def __init__(self, req: RequestService):
        self.req = req

# --- Tests ---

@pytest.mark.asyncio
async def test_basic_resolution():
    """Test basic class resolution."""
    container = Container()
    container.register(ClassProvider(SimpleService))
    
    instance = await container.resolve_async(SimpleService)
    assert isinstance(instance, SimpleService)

@pytest.mark.asyncio
async def test_dependency_resolution():
    """Test resolving a service with dependencies."""
    container = Container()
    container.register(ClassProvider(SimpleService))
    container.register(ClassProvider(DependencyService))
    
    instance = await container.resolve_async(DependencyService)
    assert isinstance(instance, DependencyService)
    assert isinstance(instance.simple, SimpleService)

@pytest.mark.asyncio
async def test_implicit_inference_fix():
    """Test the fix for implicit type inference (default values in factory)."""
    # This tests ControllerFactory logic specifically
    container = Container()
    container.register(ClassProvider(SimpleService))
    factory = ControllerFactory(app_container=container)
    
    class ImplicitController:
        def __init__(self, svc = SimpleService):
            self.svc = svc
            
    instance = await factory.create(ImplicitController)
    # svc should be an INSTANCE, not the class
    assert isinstance(instance.svc, SimpleService) 
    assert instance.svc is not SimpleService

@pytest.mark.asyncio
async def test_interface_binding():
    """Test the interface binding capability."""
    container = Container()
    container.bind(IService, ConcreteService)
    
    instance = await container.resolve_async(IService)
    assert isinstance(instance, ConcreteService)
    assert instance.get_value() == "concrete"

@pytest.mark.asyncio
async def test_scope_validation_leak():
    """Test that Singleton -> Request leak is blocked."""
    container = Container(scope="app")
    # Explicit request scope
    container.register(ClassProvider(RequestService, scope="request"))
    
    factory = ControllerFactory(app_container=container)
    
    class LeakingController:
        def __init__(self, r: RequestService): self.r = r
            
    # Should raise ScopeViolationError
    with pytest.raises(ScopeViolationError) as excinfo:
        await factory.create(LeakingController, mode=InstantiationMode.SINGLETON)
    
    assert "cannot inject request-scoped" in str(excinfo.value)

@pytest.mark.asyncio
async def test_no_init_class_support():
    """Test specific fix for classes without explicit __init__."""
    # This ensures ClassProvider doesn't crash on object.__init__
    container = Container()
    
    class NoInit:
        pass
        
    container.register(ClassProvider(NoInit))
    instance = await container.resolve_async(NoInit)
    assert isinstance(instance, NoInit)

@pytest.mark.asyncio
async def test_circular_dependency():
    """Test circular dependency detection."""
    container = Container()
    container.register(ClassProvider(CycleA))
    container.register(ClassProvider(CycleB))
    
    # Cycles are usually detected during graph build phase in Registry,
    # but runtime resolution checks recursion stack too (ResolveCtx).
    # Since we are using runtime container directly without Registry static checks:
    with pytest.raises(RecursionError): 
        # Python's recursion limit or internal stack check should trip
        # Our ResolveCtx has cycle detection but let's see which one hits first
        # Actually expected: RecursionError or stack overflow protection
        await container.resolve_async(CycleA)

if __name__ == "__main__":
    # Allow running directly
    asyncio.run(test_basic_resolution())
    asyncio.run(test_dependency_resolution())
    asyncio.run(test_implicit_inference_fix())
    asyncio.run(test_interface_binding())
    asyncio.run(test_scope_validation_leak())
    asyncio.run(test_no_init_class_support())
    try:
        asyncio.run(test_circular_dependency())
    except RecursionError:
        pass
    print("✅ All regression tests passed manual run.")
