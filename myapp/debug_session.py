#!/usr/bin/env python3
"""
Debug script to test session engine creation.
"""

import sys
sys.path.insert(0, '/Users/kuroyami/PyProjects/Aquilia')

from aquilia.config import ConfigLoader
from aquilia.server import AquiliaServer

def debug_session_engine():
    loader = ConfigLoader.load(paths=["workspace.py"])
    
    # Create a mock server to test session engine creation
    try:
        session_config = loader.get_session_config()
        print(f"Session config enabled: {session_config.get('enabled')}")
        print(f"Session config: {session_config}")
        
        # Try to create session engine directly
        from aquilia.sessions import SessionEngine, SessionPolicy, MemoryStore, CookieTransport
        from datetime import timedelta
        
        # Get the actual policy objects from the config
        if "policies" in session_config and session_config["policies"]:
            first_policy = session_config["policies"][0]
            print(f"First policy type: {type(first_policy)}")
            print(f"First policy: {first_policy}")
            
            if hasattr(first_policy, 'name'):
                print("Policy is an object, creating engine with workspace policy")
                store = MemoryStore(max_sessions=10000)
                transport = CookieTransport(first_policy.transport)
                engine = SessionEngine(policy=first_policy, store=store, transport=transport)
                print("✅ SessionEngine created successfully")
            else:
                print("Policy is string representation, need to create from config")
        
    except Exception as e:
        print(f"❌ Session engine creation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_session_engine()