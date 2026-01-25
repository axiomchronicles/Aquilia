#!/usr/bin/env python3
"""
Debug script to check session configuration loading.
"""

import sys
sys.path.insert(0, '/Users/kuroyami/PyProjects/Aquilia')

from aquilia.config import ConfigLoader
import json

def debug_config():
    loader = ConfigLoader.load(paths=["workspace.py"])
    
    print("=== Full Configuration ===")
    config_dict = loader.to_dict()
    print(json.dumps(config_dict, indent=2, default=str))
    
    print("\n=== Session Configuration ===")
    session_config = loader.get_session_config()
    print(json.dumps(session_config, indent=2, default=str))
    
    print(f"\nSessions enabled: {session_config.get('enabled', False)}")

if __name__ == "__main__":
    debug_config()