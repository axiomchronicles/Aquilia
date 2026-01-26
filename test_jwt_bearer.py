import httpx
import asyncio
import uuid

BASE_URL = "http://localhost:8000/myappmod"

async def test_jwt_bearer():
    print("🚀 Starting JWT Bearer Auth Verification...")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Generate test user
        username = f"jwt_user_{uuid.uuid4().hex[:6]}"
        password = "Password123!"
        
        # 1. Register User
        print(f"\n1. Registering User: {username}...")
        resp = await client.post(f"{BASE_URL}/auth/register", json={
            "username": username,
            "password": password,
            "roles": ["user", "jwt_tester"]
        })
        if resp.status_code != 201:
            print(f"❌ FAIL - Registration: {resp.status_code} {resp.text}")
            return
        print("✅ PASS - User Registered")
        
        # 2. Login to obtain JWT
        print(f"2. Logging in as {username}...")
        resp = await client.post(f"{BASE_URL}/auth/login", json={
            "username": username,
            "password": password
        })
        if resp.status_code != 200:
            print(f"❌ FAIL - Login: {resp.status_code} {resp.text}")
            return
        
        data = resp.json()
        access_token = data.get("access_token")
        if not access_token:
            print("❌ FAIL - No access token in response")
            return
        print("✅ PASS - Logged In (Token obtained)")
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # 3. Access Protected Route with valid token
        print("\n3. Accessing /jwt/protected with valid Bearer token...")
        resp = await client.get(f"{BASE_URL}/jwt/protected", headers=headers)
        if resp.status_code == 200:
            print(f"✅ PASS - Protected Access: {resp.json().get('message')}")
        else:
            print(f"❌ FAIL - Expected 200, got {resp.status_code} {resp.text}")
            
        # 4. Access Protected Route without token
        print("4. Accessing /jwt/protected WITHOUT token (clearing cookies first)...")
        client.cookies.clear()
        resp = await client.get(f"{BASE_URL}/jwt/protected")
        if resp.status_code == 403:
            print("✅ PASS - Access Denied (Correct 403)")
        else:
            print(f"❌ FAIL - Expected 403, got {resp.status_code} {resp.text}")
            
        # 5. Access Protected Route with invalid token
        print("5. Accessing /jwt/protected with INVALID token...")
        client.cookies.clear()
        invalid_headers = {"Authorization": "Bearer invalid_token_here"}
        resp = await client.get(f"{BASE_URL}/jwt/protected", headers=invalid_headers)
        if resp.status_code == 403:
            print("✅ PASS - Access Denied for invalid token (Correct 403)")
        else:
            print(f"❌ FAIL - Expected 403, got {resp.status_code} {resp.text}")
            
        # 6. Verify Claims via /jwt/info
        print("\n6. Verifying JWT Claims via /jwt/info...")
        resp = await client.get(f"{BASE_URL}/jwt/info", headers=headers)
        if resp.status_code == 200:
            info = resp.json()
            print(f"✅ PASS - Claims Verified: Roles={info.get('roles')}")
            if "jwt_tester" in info.get("roles", []):
                print("✅ PASS - Custom role 'jwt_tester' found in claims")
            else:
                print(f"❌ FAIL - Custom role not found. Roles: {info.get('roles')}")
        else:
            print(f"❌ FAIL - Expected 200, got {resp.status_code} {resp.text}")

        print("\n✨ JWT Bearer Auth Verification Completed!")

if __name__ == "__main__":
    asyncio.run(test_jwt_bearer())
