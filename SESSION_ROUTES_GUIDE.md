#!/usr/bin/env python3
"""
Session Routes Usage Guide and Example
Shows how to properly use the session routes
"""

import json

# Example usage with curl:
print("=" * 70)
print("SESSION ROUTES - USAGE GUIDE")
print("=" * 70)
print()

print("Prerequisites: Start server with 'aq run' or 'python myapp/workspace.py'")
print()

print("=" * 70)
print("1. LOGIN - Create a session")
print("=" * 70)
print()
print("curl -X POST http://localhost:8000/mymodule/session/login \\")
print("  -H 'Content-Type: application/json' \\")
print("  -d '{\"username\": \"alice\", \"password\": \"secret\"}' \\")
print("  -v")
print()
print("Response:")
print(json.dumps({
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "user": "alice",
    "message": "Login successful"
}, indent=2))
print()
print("Note the session ID and Set-Cookie header from the response!")
print()

print("=" * 70)
print("2. GET PROFILE - Retrieve session data")
print("=" * 70)
print()
print("curl -X GET http://localhost:8000/mymodule/session/profile \\")
print("  -H 'Cookie: mymodule_session=550e8400-e29b-41d4-a716-446655440000' \\")
print("  -v")
print()
print("Response:")
print(json.dumps({
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "alice",
    "created_at": "2026-01-25T16:15:00.120619",
    "last_activity": "2026-01-25T16:15:00.120645",
    "data": {
        "login_time": "2026-01-25T16:15:00"
    }
}, indent=2))
print()

print("=" * 70)
print("3. UPDATE SESSION - Modify session data")
print("=" * 70)
print()
print("curl -X POST http://localhost:8000/mymodule/session/update \\")
print("  -H 'Content-Type: application/json' \\")
print("  -H 'Cookie: mymodule_session=550e8400-e29b-41d4-a716-446655440000' \\")
print("  -d '{\"preferences\": {\"theme\": \"dark\"}, \"language\": \"en\"}' \\")
print("  -v")
print()
print("Response:")
print(json.dumps({
    "message": "Session updated",
    "session_id": "550e8400-e29b-41d4-a716-446655440000"
}, indent=2))
print()

print("=" * 70)
print("4. LOGOUT - Invalidate session")
print("=" * 70)
print()
print("curl -X POST http://localhost:8000/mymodule/session/logout \\")
print("  -H 'Cookie: mymodule_session=550e8400-e29b-41d4-a716-446655440000' \\")
print("  -v")
print()
print("Response:")
print(json.dumps({
    "message": "Logout successful"
}, indent=2))
print()

print("=" * 70)
print("PYTHON EXAMPLE WITH REQUESTS")
print("=" * 70)
print()
print("""
import requests

# Create a session to persist cookies across requests
session = requests.Session()

# 1. Login
print("1. Logging in...")
resp = session.post(
    "http://localhost:8000/mymodule/session/login",
    json={"username": "bob", "password": "pass123"}
)
print(f"   Status: {resp.status_code}")
login_data = resp.json()
print(f"   Session ID: {login_data['session_id']}")

# 2. Get profile (cookies automatically sent)
print("2. Getting profile...")
resp = session.get("http://localhost:8000/mymodule/session/profile")
print(f"   Status: {resp.status_code}")
profile = resp.json()
print(f"   Username: {profile['username']}")
print(f"   Created at: {profile['created_at']}")

# 3. Update session
print("3. Updating session...")
resp = session.post(
    "http://localhost:8000/mymodule/session/update",
    json={"preferences": {"theme": "dark", "notifications": True}}
)
print(f"   Status: {resp.status_code}")
print(f"   Message: {resp.json()['message']}")

# 4. Logout
print("4. Logging out...")
resp = session.post("http://localhost:8000/mymodule/session/logout")
print(f"   Status: {resp.status_code}")
print(f"   Message: {resp.json()['message']}")
""")
print()

print("=" * 70)
print("ARCHITECTURE")
print("=" * 70)
print("""
HTTP Request
    ↓
Route Handler (no decorator - manual session management)
    ↓
Controller Method (injected with SessionTrackingService via DI)
    ↓
SessionTrackingService
    ├─ Creates session with UUID
    ├─ Stores in memory dict
    └─ Tracks in DI singleton
    
HTTP Response
    ├─ Returns JSON with session_id
    └─ Browser stores Set-Cookie header
    
Next Request
    ├─ Browser sends cookie
    ├─ Controller accesses ctx.session
    ├─ Uses session_id to lookup in SessionTrackingService
    └─ Returns user data
""")
print()

print("=" * 70)
print("KEY POINTS")
print("=" * 70)
print("""
✓ No session decorators - manual session management
✓ SessionTrackingService tracks all sessions in memory
✓ Each session gets a UUID as ID
✓ Sessions stored with username, timestamps, and custom data
✓ Profile/Update/Logout require active session (manual check)
✓ Session data preserved in service across requests
✓ DI container provides singleton SessionTrackingService
✓ Cookies handled by HTTP client (requests/httpx) or browser
""")
print()
