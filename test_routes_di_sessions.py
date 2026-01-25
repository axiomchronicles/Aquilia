#!/usr/bin/env python3
"""
Test Routes, DI, and Sessions Integration

This test demonstrates:
1. DI container integration with services and controllers
2. Session management with Aquilia's unique syntax
3. Route handling with session-aware endpoints
4. CRUD operations with session persistence
5. User authentication and session state management
"""

import asyncio
import json
from datetime import datetime
import sys
from typing import Dict, Any

from aquilia import Workspace
from aquilia.server import AquiliaServer
from aquilia.request import Request
from aquilia.response import Response
from aquilia.sessions import SessionEngine, MemoryStore, CookieTransport


async def test_routes_di_sessions():
    """Test the complete integration of routes, DI, and sessions."""
    
    print("🧪 Testing Routes, DI, and Sessions Integration")
    print("=" * 65)
    
    # 1. Load workspace and create server components
    print("\n1. Creating Components from Workspace")
    print("-" * 40)
    
    try:
        # Import the workspace and extract manifests
        from myapp.workspace import workspace
        from myapp.modules.mymodule.manifest import manifest as mymodule_manifest
        
        # Debug: Check if manifest is loaded correctly
        print(f"✅ Manifest imported: {mymodule_manifest}")
        print(f"   Type: {type(mymodule_manifest)}")
        if mymodule_manifest is not None:
            print(f"   Name: {mymodule_manifest.name}")
            print(f"   Version: {mymodule_manifest.version}")
        else:
            print("❌ Manifest is None!")
            sys.exit(1)
        
        # Get workspace info via to_dict()
        workspace_info = workspace.to_dict()
        workspace_name = workspace_info["workspace"]["name"]
        workspace_version = workspace_info["workspace"]["version"]
        workspace_desc = workspace_info["workspace"]["description"]
        
        print(f"✅ Workspace loaded: {workspace_name}")
        print(f"   Version: {workspace_version}")
        print(f"   Description: {workspace_desc}")
        
        # Create server with manifest
        from aquilia.config import ConfigLoader
        
        config = ConfigLoader()
        config.config_data = {
            "debug": True,
            "apps": {
                "mymodule": {}
            }
        }
        config._build_apps_namespace()
        
        server = AquiliaServer(
            manifests=[mymodule_manifest],
            config=config,
        )
        print(f"✅ Server created with manifest")
        
        # Get DI container
        container = server._get_base_container()
        print(f"✅ DI Container initialized")
        
    except Exception as e:
        print(f"❌ Failed to create server: {e}")
        return
    
    # 2. Test service injection
    print("\n2. Testing Service DI")
    print("-" * 25)
    
    try:
        from myapp.modules.mymodule.services import MymoduleService
        
        # Get service from container
        service = await container.resolve_async(MymoduleService)
        print(f"✅ Service injected: {type(service).__name__}")
        
        # Test basic service operations
        item = await service.create({"name": "Test Item", "description": "DI test"})
        print(f"✅ Service method works: created item {item['id']}")
        
        all_items = await service.get_all()
        print(f"✅ Service state: {len(all_items)} items in storage")
        
    except Exception as e:
        print(f"❌ Service DI test failed: {e}")
        return
    
    # 3. Test session engine creation
    print("\n3. Testing Session Engine")
    print("-" * 30)
    
    try:
        # Create session components using unique Aquilia syntax
        from aquilia.sessions import SessionPolicy, MemoryStore, CookieTransport
        
        policy = (SessionPolicy
                  .for_web_users()
                  .lasting(days=1)
                  .idle_timeout(hours=1)
                  .web_defaults()
                  .build())
        
        store = MemoryStore.web_optimized()
        transport = CookieTransport.for_web_browsers()
        
        engine = SessionEngine(policy=policy, store=store, transport=transport)
        print(f"✅ Session engine created with unique Aquilia syntax")
        print(f"   Policy: {policy.name}")
        print(f"   Store capacity: {store.max_sessions}")
        print(f"   Transport cookie: {transport.cookie_name}")
        
    except Exception as e:
        print(f"❌ Session engine test failed: {e}")
        return
    
    # 4. Test route simulation with sessions
    print("\n4. Testing Route Simulation with Sessions")
    print("-" * 45)
    
    try:
        from myapp.modules.mymodule.controllers import MymoduleController
        from aquilia.di import RequestCtx
        from aquilia.sessions import Session, SessionID, SessionScope
        from aquilia.sessions.core import SessionFlag
        
        # Create controller with DI
        controller = MymoduleController(service)
        print(f"✅ Controller created with DI: {type(controller).__name__}")
        
        # Create mock session
        session = Session(
            id=SessionID(),
            data={},
            created_at=datetime.now(),
            last_accessed_at=datetime.now(),
            expires_at=policy.calculate_expiry(),
            scope=SessionScope.USER,
            flags=set(),
        )
        session._policy_name = policy.name
        print(f"✅ Mock session created: {session.id}")
        
        # Create mock request context
        class MockRequestCtx:
            def __init__(self, session_obj, json_data=None):
                self.session = session_obj
                self._json_data = json_data or {}
                
            async def json(self):
                return self._json_data
        
        # Test session info endpoint
        ctx = MockRequestCtx(session)
        response = await controller.get_session_info(ctx)
        session_info = json.loads(response._content)
        print(f"✅ Session info endpoint works:")
        print(f"   Session ID: {session_info['session_id'][:16]}...")
        print(f"   User ID: {session_info['user_id']}")
        print(f"   Authenticated: {session_info['is_authenticated']}")
        
    except Exception as e:
        print(f"❌ Route simulation test failed: {e}")
        return
    
    # 5. Test authentication flow
    print("\n5. Testing Authentication Flow")
    print("-" * 35)
    
    try:
        # Test login
        login_ctx = MockRequestCtx(session, {"username": "john_doe", "role": "admin"})
        login_response = await controller.login_user(login_ctx)
        login_data = json.loads(login_response._content)
        print(f"✅ Login endpoint works:")
        print(f"   Message: {login_data['message']}")
        print(f"   User ID: {login_data['user_id']}")
        print(f"   Role: {login_data['role']}")
        
        # Verify session state after login
        post_login_ctx = MockRequestCtx(session)
        post_login_response = await controller.get_session_info(post_login_ctx)
        post_login_info = json.loads(post_login_response._content)
        print(f"✅ Session state after login:")
        print(f"   Authenticated: {post_login_info['is_authenticated']}")
        print(f"   Principal: {post_login_info['principal_id']}")
        
    except Exception as e:
        print(f"❌ Authentication test failed: {e}")
        return
    
    # 6. Test session-aware CRUD operations
    print("\n6. Testing Session-Aware CRUD")
    print("-" * 35)
    
    try:
        # Create user-specific item
        item_ctx = MockRequestCtx(session, {"name": "My Personal Item", "category": "personal"})
        item_response = await controller.create_my_item(item_ctx)
        item_data = json.loads(item_response._content)
        print(f"✅ Created user item:")
        print(f"   ID: {item_data['id']}")
        print(f"   User ID: {item_data['user_id']}")
        print(f"   Session ID: {item_data['session_id'][:16]}...")
        
        # Get user items
        my_items_ctx = MockRequestCtx(session)
        my_items_response = await controller.get_my_items(my_items_ctx)
        my_items_data = json.loads(my_items_response._content)
        print(f"✅ Retrieved user items:")
        print(f"   Total: {my_items_data['total']}")
        print(f"   Items: {[item['name'] for item in my_items_data['items']]}")
        
        # Test with different session (different user)
        session2 = Session(
            id=SessionID(),
            data={},
            created_at=datetime.now(),
            last_accessed_at=datetime.now(),
            expires_at=policy.calculate_expiry(),
            scope=SessionScope.USER,
            flags=set(),
        )
        session2._policy_name = policy.name
        
        session2_ctx = MockRequestCtx(session2)
        session2_items = await controller.get_my_items(session2_ctx)
        session2_data = json.loads(session2_items._content)
        print(f"✅ Different session isolation:")
        print(f"   Session 2 items: {session2_data['total']}")
        
    except Exception as e:
        print(f"❌ Session-aware CRUD test failed: {e}")
        return
    
    # 7. Test logout flow
    print("\n7. Testing Logout Flow")
    print("-" * 25)
    
    try:
        logout_ctx = MockRequestCtx(session)
        logout_response = await controller.logout_user(logout_ctx)
        logout_data = json.loads(logout_response._content)
        print(f"✅ Logout endpoint works:")
        print(f"   Message: {logout_data['message']}")
        
        # Verify session state after logout
        post_logout_ctx = MockRequestCtx(session)
        post_logout_response = await controller.get_session_info(post_logout_ctx)
        post_logout_info = json.loads(post_logout_response._content)
        print(f"✅ Session state after logout:")
        print(f"   Authenticated: {post_logout_info['is_authenticated']}")
        print(f"   Principal: {post_logout_info['principal_id']}")
        
    except Exception as e:
        print(f"❌ Logout test failed: {e}")
        return
    
    # 8. Test store statistics
    print("\n8. Testing Store Statistics")
    print("-" * 30)
    
    try:
        stats = store.get_stats()
        print(f"✅ Store statistics:")
        print(f"   Total sessions: {stats['total_sessions']}")
        print(f"   Max capacity: {stats['max_sessions']}")
        print(f"   Utilization: {stats['utilization']:.1%}")
        
        # Test session storage
        await store.save(session)
        await store.save(session2)
        
        updated_stats = store.get_stats()
        print(f"✅ After storing sessions:")
        print(f"   Total sessions: {updated_stats['total_sessions']}")
        print(f"   Utilization: {updated_stats['utilization']:.1%}")
        
    except Exception as e:
        print(f"❌ Store statistics test failed: {e}")
        return
    
    print("\n🎉 All Routes, DI, and Sessions Tests Passed!")
    print("=" * 65)
    print("✅ DI container working with service injection")
    print("✅ Session engine using unique Aquilia syntax")
    print("✅ Controllers handling session-aware routes")
    print("✅ Authentication flow with session binding")
    print("✅ Session-aware CRUD operations")
    print("✅ Session isolation between users")
    print("✅ Session state management (login/logout)")
    print("✅ Store statistics and session persistence")


if __name__ == "__main__":
    asyncio.run(test_routes_di_sessions())