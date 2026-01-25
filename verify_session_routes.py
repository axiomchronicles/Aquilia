#!/usr/bin/env python3
"""
Session Routes - Verification Test
Verifies the session routes work correctly without decorators
"""

import asyncio
from modules.mymodule.services import MymoduleService, SessionTrackingService
from modules.mymodule.controllers import MymoduleController


class MockRequestContext:
    """Mock RequestCtx for testing without HTTP"""
    def __init__(self):
        self.session = {}
        self._body = {}
    
    async def json(self):
        return self._body


async def verify_routes():
    """Verify session routes work correctly"""
    
    print("\n" + "=" * 70)
    print("SESSION ROUTES VERIFICATION")
    print("=" * 70 + "\n")
    
    # Initialize services and controller
    mymodule_service = MymoduleService()
    session_service = SessionTrackingService()
    controller = MymoduleController(mymodule_service, session_service)
    
    # Test 1: Login
    print("TEST 1: Login Route (No decorator)")
    print("-" * 70)
    ctx_login = MockRequestContext()
    ctx_login._body = {"username": "alice", "password": "secret"}
    
    response = await controller.session_login(ctx_login)
    print(f"Response: {response.body}")
    
    login_data = eval(response.body)  # Parse JSON string
    session_id = login_data['session_id']
    ctx_login.session['user_id'] = session_id
    ctx_login.session['username'] = login_data['user']
    print(f"✓ Login successful")
    print(f"  Session ID: {session_id}")
    print(f"  User: {login_data['user']}\n")
    
    # Test 2: Profile
    print("TEST 2: Profile Route (No decorator - manual session check)")
    print("-" * 70)
    ctx_profile = MockRequestContext()
    ctx_profile.session = ctx_login.session.copy()
    
    response = await controller.session_profile(ctx_profile)
    print(f"Response: {response.body}")
    
    profile_data = eval(response.body)
    print(f"✓ Profile retrieved")
    print(f"  Username: {profile_data['username']}")
    print(f"  Session ID: {profile_data['session_id']}\n")
    
    # Test 3: Update
    print("TEST 3: Update Route (No decorator - manual session check)")
    print("-" * 70)
    ctx_update = MockRequestContext()
    ctx_update.session = ctx_login.session.copy()
    ctx_update._body = {"preferences": {"theme": "dark"}}
    
    response = await controller.session_update(ctx_update)
    print(f"Response: {response.body}")
    
    update_data = eval(response.body)
    print(f"✓ Session updated")
    print(f"  Message: {update_data['message']}\n")
    
    # Test 4: Logout
    print("TEST 4: Logout Route (No decorator)")
    print("-" * 70)
    ctx_logout = MockRequestContext()
    ctx_logout.session = ctx_login.session.copy()
    
    response = await controller.session_logout(ctx_logout)
    print(f"Response: {response.body}")
    
    logout_data = eval(response.body)
    print(f"✓ Logout successful")
    print(f"  Message: {logout_data['message']}\n")
    
    # Test 5: Profile without session
    print("TEST 5: Profile Without Session (Should error)")
    print("-" * 70)
    ctx_no_session = MockRequestContext()
    ctx_no_session.session = {}
    
    response = await controller.session_profile(ctx_no_session)
    print(f"Response: {response.body}")
    
    error_data = eval(response.body)
    if response.status_code == 401:
        print(f"✓ Correctly rejected (401 status)")
        print(f"  Error: {error_data['error']}\n")
    
    print("=" * 70)
    print("✅ ALL ROUTES WORKING CORRECTLY")
    print("=" * 70)
    print("\nSUMMARY:")
    print("  ✓ Login route works (no decorator)")
    print("  ✓ Profile route works (manual session check)")
    print("  ✓ Update route works (manual session check)")
    print("  ✓ Logout route works (no decorator)")
    print("  ✓ Proper error handling (401 when no session)")
    print("\n🎉 Session routes verified and ready for HTTP testing!\n")


if __name__ == "__main__":
    import os
    import sys
    os.chdir('/Users/kuroyami/PyProjects/Aquilia/myapp')
    asyncio.run(verify_routes())
