import sys
import os

# Add current directory to path
sys.path.insert(0, os.getcwd())

try:
    from authentication.modules.auth.controllers import AuthController
    from aquilia import Controller

    print(f"Controller Prefix: '{AuthController.prefix}'")
    print("-" * 40)
    
    # Inspect all attributes
    routes_found = False
    for name in dir(AuthController):
        attr = getattr(AuthController, name)
        # Check for our decorators markers (this depends on Aquilia internals, 
        # but typically they set _route_path or similar)
        # Let's try to just print anything that looks like a route
        if hasattr(attr, "_route_path"):
             print(f"[{attr._route_method}] '{attr._route_path}' -> {name}")
             routes_found = True
        elif hasattr(attr, "__dict__") and "_route_path" in attr.__dict__:
             # Inspect wrapped functions
             print(f"[{attr._route_method}] '{attr._route_path}' -> {name}")
             routes_found = True

    if not routes_found:
        print("No routes found via inspection. Checking explicit 'routes' list if it exists...")

except Exception as e:
    print(f"Error: {e}")
