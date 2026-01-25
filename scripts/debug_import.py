
import sys
import os
import importlib
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.getcwd())

service_path = "modules.mymod.services:MymodService"

print(f"Trying to import: {service_path}")

try:
    if ":" in service_path:
        module_path, class_name = service_path.split(":", 1)
    else:
        module_path, class_name = service_path.rsplit(".", 1)
    
    print(f"  Module: {module_path}")
    print(f"  Class: {class_name}")

    module = importlib.import_module(module_path)
    print(f"  Module imported: {module}")
    service_class = getattr(module, class_name)
    print(f"  Service class found: {service_class}")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
