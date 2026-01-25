import requests
import json

# Create a session to persist cookies
session = requests.Session()

def print_response(title, response):
    """Helper to print formatted response."""
    print(f"\n{title}:")
    print(f"Status: {response.status_code}")
    try:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
    except:
        print(f"Response: {response.text}")
    
    # Show session cookies
    cookies = session.cookies.get_dict()
    if cookies:
        print(f"Cookies: {cookies}")

print("🧪 Testing Enhanced Aquilia Sessions Integration")
print("=" * 60)

# 0. Create session explicitly first
print_response("0. CREATE SESSION", 
               session.get("http://localhost:8000/mymodule/session/create"))

# 1. Debug session (before login)
print_response("1. DEBUG SESSION (before login)", 
               session.get("http://localhost:8000/mymodule/session/debug"))

# 2. Login
print_response("2. LOGIN", 
               session.post("http://localhost:8000/mymodule/session/login", json={
                   "username": "testuser",
                   "password": "testpass"
               }))

# 3. Get profile (authenticated)
print_response("3. GET PROFILE (authenticated)", 
               session.get("http://localhost:8000/mymodule/session/profile"))

# 4. Debug session (after login)
print_response("4. DEBUG SESSION (after login)", 
               session.get("http://localhost:8000/mymodule/session/debug"))

# 5. Update session data
print_response("5. UPDATE SESSION", 
               session.post("http://localhost:8000/mymodule/session/update", json={
                   "preferences": {"theme": "dark"},
                   "profile": {"email": "testuser@example.com"},
                   "custom_data": {"custom_field": "custom_value"}
               }))

# 6. Get updated profile
print_response("6. GET UPDATED PROFILE", 
               session.get("http://localhost:8000/mymodule/session/profile"))

# 7. Track feature usage
print_response("7. TRACK FEATURE USAGE", 
               session.post("http://localhost:8000/mymodule/analytics/track", json={
                   "feature": "session_update",
                   "page": "/session"
               }))

# 8. Get analytics summary
print_response("8. ANALYTICS SUMMARY", 
               session.get("http://localhost:8000/mymodule/analytics/summary"))

# 9. Get user analytics
print_response("9. USER ANALYTICS", 
               session.get("http://localhost:8000/mymodule/analytics/user/testuser"))

# 10. Final debug session 
print_response("10. FINAL DEBUG SESSION", 
               session.get("http://localhost:8000/mymodule/session/debug"))

# 11. Logout
print_response("11. LOGOUT", 
               session.post("http://localhost:8000/mymodule/session/logout"))

# 12. Debug session (after logout)
print_response("12. DEBUG SESSION (after logout)", 
               session.get("http://localhost:8000/mymodule/session/debug"))

print("\n🎉 Session Integration Test Complete!")
print("=" * 60)