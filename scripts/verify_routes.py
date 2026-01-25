
import sys
import os
from pathlib import Path
import asyncio

# Ensure project root is in path
project_root = Path.cwd()
sys.path.insert(0, str(project_root))

def verify_routes():
    print("1. Regenerating runtime app...")
    from aquilia.cli.commands.run import _create_workspace_app
    workspace_dir = project_root / "myapp"
    _create_workspace_app(workspace_dir, mode="test", verbose=True)
    
    # Add myapp/runtime to path to import generated app
    sys.path.insert(0, str(workspace_dir))
    
    print("\n2. Importing generated app...")
    try:
        import runtime.app
        server = runtime.app.server
        
        print("   ✓ App imported successfully")
        
        async def inspect_server():
            # Configure logging
            import logging
            logging.basicConfig(level=logging.INFO)
            
            print("\n   Inspecting Aquilary Registry...")
            registry_info = server.aquilary.inspect()
            print(f"   Registry Info: {registry_info}")
            
            for app in registry_info['apps']:
                print(f"   App '{app['name']}':")
                print(f"     Controllers: {app['controllers']}")
                print(f"     Services: {app['services']}")
            
            print("\n   Running startup...")
            await server.startup()
            
            print("\n3. Inspecting routes...")
            routes = server.controller_router.get_routes()
                
            found_mymod = False
            print(f"   Found {len(routes)} routes:")
            for route in routes:
                path = route.get('path', str(route))
                print(f"   - {path}")
                if '/mymod' in path:
                    found_mymod = True
                    
            await server.shutdown()
            
            if found_mymod:
                print("\n   ✓ SUCCESS: /mymod routes discovered!")
            else:
                print("\n   ✗ FAILURE: /mymod routes NOT found!")
                sys.exit(1)

        asyncio.run(inspect_server())
            
    except ImportError as e:
        print(f"   ✗ Failed to import runtime.app: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"   ✗ Error inspecting app: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    verify_routes()
