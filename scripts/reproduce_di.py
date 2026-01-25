
import sys
import os
import asyncio
import inspect
from pathlib import Path

# Add project root
sys.path.insert(0, os.getcwd())

# Mock necessary components
from aquilia.di import Container
from aquilia.di.providers import ClassProvider
from aquilia.controller.factory import ControllerFactory

async def reproduce():
    print("--- DI Reproduction Script ---")
    
    # 1. Setup Container
    container = Container(scope="app")
    
    # 2. Register Service
    try:
        from modules.mymod.services import MymodService
        provider = ClassProvider(cls=MymodService, scope="app")
        container.register(provider)
        print(f"✓ Registered {MymodService}")
    except Exception as e:
        print(f"❌ Failed to register service: {e}")
        return

    # 3. Import Controller
    try:
        from modules.mymod.controllers import MymodController
        print(f"✓ Imported {MymodController}")
    except Exception as e:
        print(f"❌ Failed to import controller: {e}")
        return
        
    # 4. Check Signature
    sig = inspect.signature(MymodController.__init__)
    print(f"Signature: {sig}")
    for name, param in sig.parameters.items():
        if name == 'self': continue
        print(f"  Param: {name}, Annotation: {param.annotation} (Type: {type(param.annotation)})")
        
    # 5. Try Factory Resolution
    factory = ControllerFactory(app_container=container)
    
    print("\nAttempting creation...")
    try:
        instance = await factory.create(MymodController)
        print(f"✓ Successfully created instance: {instance}")
        print(f"  Service: {instance.service}")
    except Exception as e:
        print(f"❌ Factory creation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(reproduce())
