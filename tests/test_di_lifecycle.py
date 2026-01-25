import asyncio
import unittest
from aquilia.di import Container

class TestService:
    def __init__(self):
        self.started = False
        self.stopped = False
        
    async def on_startup(self):
        self.started = True
        
    async def on_shutdown(self):
        self.stopped = True

class TestDILifecycle(unittest.IsolatedAsyncioTestCase):
    async def test_lifecycle_hooks(self):
        container = Container()
        from aquilia.di.providers import ClassProvider
        
        provider = ClassProvider(TestService, scope="app")
        container.register(provider)
        
        # Resolve to trigger registration of hooks
        service = await container.resolve_async(TestService)
        self.assertFalse(service.started)
        
        # Run startup
        await container.startup()
        self.assertTrue(service.started)
        
        # Run shutdown
        await container.shutdown()
        self.assertTrue(service.stopped)

if __name__ == "__main__":
    unittest.main()
