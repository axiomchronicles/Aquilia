#!/usr/bin/env python3
"""
End-to-End Session Route Test
Tests the actual HTTP session routes with proper cookie handling
"""

import asyncio
import httpx
import sys

async def test_session_routes():
    """Test session routes with HTTP client"""
    
    # Give server time to start if needed
    await asyncio.sleep(1)
    
    base_url = "http://localhost:8000"
    
    try:
        # Use httpx with cookies
        async with httpx.AsyncClient() as client:
            print("=" * 70)
            print("END-TO-END SESSION ROUTES TEST")
            print("=" * 70)
            print()
            
            # Test 1: Login
            print("TEST 1: Login (POST /session/login)")
            print("-" * 70)
            try:
                response = await client.post(
                    f"{base_url}/mymodule/session/login",
                    json={"username": "testuser", "password": "secret123"},
                    follow_redirects=True
                )
                print(f"Status: {response.status_code}")
                login_data = response.json()
                print(f"Response: {login_data}")
                
                if response.status_code == 200:
                    print("✓ Login successful")
                    session_id = login_data.get("session_id")
                    print(f"  Session ID: {session_id}")
                else:
                    print(f"✗ Login failed with status {response.status_code}")
                print()
            except Exception as e:
                print(f"✗ Login error: {e}")
                print()
                return
            
            # Test 2: Get Profile (should work if session cookie persists)
            print("TEST 2: Get Profile (GET /session/profile)")
            print("-" * 70)
            try:
                response = await client.get(
                    f"{base_url}/mymodule/session/profile",
                    follow_redirects=True
                )
                print(f"Status: {response.status_code}")
                profile_data = response.json()
                print(f"Response: {profile_data}")
                
                if response.status_code == 200:
                    print("✓ Profile retrieved successfully")
                    print(f"  Username: {profile_data.get('username')}")
                elif response.status_code == 401:
                    print("✗ No active session (SESSION_REQUIRED error)")
                else:
                    print(f"✗ Profile failed with status {response.status_code}")
                print()
            except Exception as e:
                print(f"✗ Profile error: {e}")
                print()
                return
            
            # Test 3: Update Session
            print("TEST 3: Update Session (POST /session/update)")
            print("-" * 70)
            try:
                response = await client.post(
                    f"{base_url}/mymodule/session/update",
                    json={"preferences": {"theme": "dark"}},
                    follow_redirects=True
                )
                print(f"Status: {response.status_code}")
                update_data = response.json()
                print(f"Response: {update_data}")
                
                if response.status_code == 200:
                    print("✓ Session updated")
                elif response.status_code == 401:
                    print("✗ No active session")
                else:
                    print(f"✗ Update failed with status {response.status_code}")
                print()
            except Exception as e:
                print(f"✗ Update error: {e}")
                print()
            
            # Test 4: Logout
            print("TEST 4: Logout (POST /session/logout)")
            print("-" * 70)
            try:
                response = await client.post(
                    f"{base_url}/mymodule/session/logout",
                    follow_redirects=True
                )
                print(f"Status: {response.status_code}")
                logout_data = response.json()
                print(f"Response: {logout_data}")
                
                if response.status_code == 200:
                    print("✓ Logout successful")
                print()
            except Exception as e:
                print(f"✗ Logout error: {e}")
                print()
            
            print("=" * 70)
            print("END-TO-END TEST COMPLETE")
            print("=" * 70)
            
    except Exception as e:
        print(f"Connection error: {e}")
        print("Make sure the server is running on http://localhost:8000")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_session_routes())
