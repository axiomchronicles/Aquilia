import unittest
from aquilia.di import Container
from aquilia.di.diagnostics import ConsoleDiagnosticListener, DIEventType

class TestDIDiagnostics(unittest.TestCase):
    def test_diagnostics_emissions(self):
        class MockListener:
            def __init__(self):
                self.events = []
            def on_event(self, event):
                self.events.append(event)
                
        listener = MockListener()
        container = Container()
        container._diagnostics.add_listener(listener)
        
        # Test Registration Event
        from aquilia.di.providers import ValueProvider
        provider = ValueProvider(token="test", value=123)
        container.register(provider)
        
        self.assertEqual(len(listener.events), 1)
        self.assertEqual(listener.events[0].type, DIEventType.REGISTRATION)
        self.assertEqual(listener.events[0].token, "test")

        # Test Resolution Events
        import asyncio
        async def run_res():
            return await container.resolve_async("test")
            
        asyncio.run(run_res())
        
        # Should have: Registration, Resolution Start, Resolution Success
        self.assertEqual(len(listener.events), 3)
        self.assertEqual(listener.events[1].type, DIEventType.RESOLUTION_START)
        self.assertEqual(listener.events[2].type, DIEventType.RESOLUTION_SUCCESS)

if __name__ == "__main__":
    unittest.main()
